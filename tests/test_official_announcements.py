import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
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

    def test_valid_directional_announcement(self):
        result = official_announcements.validate(self.manifest())
        self.assertEqual(result["announcements"], 1)
        self.assertEqual(result["work_lanes"], ["AGENT_WORK", "GPU_WORK"])
        self.assertEqual(result["eligibility_status"], "UNVERIFIED")
        self.assertEqual(result["allocation_status"], "UNVERIFIED")

    def test_rejects_eligibility_promotion_without_artifact_or_receipt(self):
        data = self.manifest()
        data["announcements"][0]["state"] = "ELIGIBLE"
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

    def test_rejects_post_quote_url_and_lane_tampering(self):
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
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(official_announcements.ValidationError):
                    official_announcements.validate(mutation)

    def test_source_snapshot_digest_is_recomputed(self):
        data = self.manifest()
        item = data["announcements"][0]
        canonical = official_announcements.canonical_snapshot(item["source_snapshot"])
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), item["source_snapshot_sha256"])
        item["source_snapshot"]["authored_text_expanded"] = item["source_snapshot"]["authored_text_expanded"].replace(
            "From 19:31", "From 19:32"
        )
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
