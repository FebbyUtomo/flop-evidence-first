import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "official_announcements.py"
MANIFEST = ROOT / "evidence" / "official-announcements.json"
SPEC = importlib.util.spec_from_file_location("official_announcements", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load official_announcements module")
official_announcements = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(official_announcements)


class OfficialAnnouncementsTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_valid_multi_announcement_manifest(self):
        result = official_announcements.validate(self.manifest())
        self.assertEqual(result["announcements"], 5)
        self.assertEqual(result["work_lanes"], ["AGENT_WORK", "GPU_WORK"])
        self.assertEqual(result["states"], {
            "DIRECTIONAL_NOT_ELIGIBILITY_CRITERION": 1,
            "PREVIEW_PROVISIONAL_INACTIVE": 4,
        })
        self.assertEqual(result["eligibility_status"], "UNVERIFIED")
        self.assertEqual(result["allocation_status"], "UNVERIFIED")

    def test_kol_preview_pins_posts_media_and_fail_closed_markers(self):
        data = self.manifest()
        by_id = {item["id"]: item for item in data["announcements"]}
        self.assertEqual(set(by_id), {
            "gpu_agent_work_direction",
            "kol_leaderboard_preview",
            "kol_join_preview",
            "kol_referral_preview",
            "kol_official_quote_preview",
        })
        expected_posts = {
            "kol_leaderboard_preview": "2110624608890282056",
            "kol_join_preview": "2110624611604037995",
            "kol_referral_preview": "2110624614233845768",
            "kol_official_quote_preview": "2110628169476981128",
        }
        for ident, post_id in expected_posts.items():
            item = by_id[ident]
            self.assertEqual(item["source"]["post_id"], post_id)
            self.assertEqual(item["state"], "PREVIEW_PROVISIONAL_INACTIVE")
            self.assertIsNone(item["deadline"])
            self.assertIsNone(item["exact_identity_receipt"])
        markers = set(by_id["kol_leaderboard_preview"]["required_markers"])
        self.assertIn("PROVISIONAL · SAMPLE DATA", markers)
        self.assertIn("Weekly payout pool: To be announced", markers)
        referral_markers = set(by_id["kol_referral_preview"]["required_markers"])
        self.assertIn("Payouts and the work-weighted lottery are inactive", referral_markers)
        self.assertIn("period boundaries, eligibility and reward caps still need agreement", referral_markers)
        self.assertEqual(
            by_id["kol_official_quote_preview"]["quoted_post_ids"],
            ["2110624608890282056"],
        )
        media = by_id["kol_leaderboard_preview"]["media"]
        self.assertEqual(media[0]["sha256"], "3f8c3276b76706e9ef09ae88bf05203fcbc1226e3098bef4b3e78e534560f987")

    def test_rejects_eligibility_promotion_without_artifact_or_receipt(self):
        data = self.manifest()
        data["announcements"][1]["state"] = "ELIGIBLE"
        with self.assertRaises(official_announcements.ValidationError):
            official_announcements.validate(data)

        data = self.manifest()
        data["eligibility_status"] = "ELIGIBLE"
        with self.assertRaises(official_announcements.ValidationError):
            official_announcements.validate(data)

    def test_rejects_contradictory_claim_boundary(self):
        data = self.manifest()
        data["claim_boundary"] += " This DOES establish eligibility, allocation, and payment."
        with self.assertRaises(official_announcements.ValidationError):
            official_announcements.validate(data)

    def test_rejects_post_quote_url_lane_and_preview_tampering(self):
        mutations = []
        data = self.manifest()
        data["announcements"][0]["source"]["post_id"] = "2105090680314069402"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][0]["exact_quote"] += " guaranteed"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][0]["source"]["url"] = "https://x.com/example/status/2105090680314069401"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][0]["work_lanes"] = ["AGENT_WORK", "AIRDROP"]
        mutations.append(data)
        data = self.manifest()
        data["announcements"][0]["source"]["published_at"] = "2026-09-30T00:21:44Z"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][0]["source"]["account"] = "example"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][1]["required_markers"].remove("PROVISIONAL · SAMPLE DATA")
        mutations.append(data)
        data = self.manifest()
        data["announcements"][3]["deadline"] = "2026-09-08T00:00:00Z"
        mutations.append(data)
        data = self.manifest()
        data["announcements"][1]["media"][0]["sha256"] = "0" * 64
        mutations.append(data)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(official_announcements.ValidationError):
                    official_announcements.validate(mutation)

    def test_source_snapshot_digests_are_recomputed(self):
        data = self.manifest()
        for item in data["announcements"]:
            canonical = official_announcements.canonical_snapshot(item["source_snapshot"])
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), item["source_snapshot_sha256"])
        data["announcements"][1]["source_snapshot"]["authored_text_raw"] += " altered"
        with self.assertRaises(official_announcements.ValidationError):
            official_announcements.validate(data)

    def test_rejects_pretend_deadline_artifact_or_receipt(self):
        for field, value in (
            ("deadline", "2026-10-01T00:00:00Z"),
            ("linked_artifact", "https://example.com/task"),
            ("exact_identity_receipt", "https://example.com/receipt"),
        ):
            data = self.manifest()
            data["announcements"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(official_announcements.ValidationError):
                    official_announcements.validate(data)

    def test_rejects_missing_local_media_evidence(self):
        data = self.manifest()
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(official_announcements, "MEDIA_DIR", Path(tmp)):
                with self.assertRaises(official_announcements.ValidationError):
                    official_announcements.validate(data)

    def test_rejects_duplicate_json_keys(self):
        duplicate = '{"schema":"first","schema":"second"}'
        with self.assertRaises(official_announcements.ValidationError):
            official_announcements.loads_strict(duplicate)

    def test_non_string_lane_has_controlled_cli_error(self):
        data = self.manifest()
        data["announcements"][0]["work_lanes"] = ["GPU_WORK", {"bad": "lane"}]
        malformed = ROOT / "evidence" / ".official-announcements-malformed-test.json"
        try:
            malformed.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MODULE), str(malformed)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("official_announcements_invalid:ValidationError:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        finally:
            malformed.unlink(missing_ok=True)

    def test_cli_is_deterministic_read_only_and_optimization_safe(self):
        before = MANIFEST.read_bytes()
        command = [sys.executable, str(MODULE), str(MANIFEST)]
        normal = subprocess.run(command, text=True, capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, "-O", str(MODULE), str(MANIFEST)], text=True, capture_output=True, check=False)
        self.assertEqual(normal.returncode, 0, normal.stderr)
        self.assertEqual(optimized.returncode, 0, optimized.stderr)
        self.assertEqual(normal.stdout, optimized.stdout)
        self.assertEqual(before, MANIFEST.read_bytes())

    def test_module_has_no_network_signing_or_write_path(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertTrue(calls.isdisjoint({"urlopen", "write", "write_text", "write_bytes", "sign", "post"}))
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn("private_key", source)
        self.assertNotIn("mnemonic", source)


if __name__ == "__main__":
    unittest.main()
