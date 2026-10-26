import ast

import importlib.util
import json
import subprocess
import sys
import tempfile

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "criteria_monitor.py"
MANIFEST = ROOT / "evidence" / "official-criteria.json"
CAPTURE_FIXTURE = ROOT / "evidence" / "fixtures" / "official-criteria-2026-10-26.json"
SPEC = importlib.util.spec_from_file_location("criteria_monitor", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load criteria_monitor module")
criteria_monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(criteria_monitor)


class CriteriaMonitorTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def fetched(self, data):
        values = {}
        for source in data["sources"]:
            text = " | ".join(source["required_markers"])
            source["baseline_sha256"] = criteria_monitor.text_digest(text)
            values[source["url"]] = text
        return values

    def test_valid_baseline_is_unchanged(self):
        data = self.manifest()
        result = criteria_monitor.evaluate(data, self.fetched(data).__getitem__)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["sources_checked"], 8)
        self.assertEqual(result["material_changes"], [])
        self.assertEqual(result["allocation_status"], "UNVERIFIED")
        self.assertEqual(result["yellowpaper_commit"], "56410c67b11292e707d32ef32e9c4ff9c02e28c7")
        self.assertIn("technocore_vs_settled_compute", result["known_draft_conflicts"])

    def test_pins_new_testnet_and_airdrop_rules(self):
        data = self.manifest()
        by_id = {source["id"]: source for source in data["sources"]}
        self.assertEqual(set(by_id), {
            "teaser", "yellowpaper", "agent", "miner", "protocol_parameters",
            "testnet", "airdrop", "yellowpaper_changelog",
        })
        testnet = " | ".join(by_id["testnet"]["required_markers"])
        airdrop = " | ".join(by_id["airdrop"]["required_markers"])
        for marker in (
            "compute purchased in settled sessions",
            "One participant, one score",
            "Independent demand only",
            "published, finalized block height",
            "lodge a dispute within the stated window",
        ):
            self.assertIn(marker, testnet)
        for marker in (
            "4,400,000,000 (24.3%)",
            "There is no claim window and no deadline",
            "Every 3 $FLOP of the locked balance spent in settled sessions unlocks 1 $FLOP",
            "Nothing liquid",
        ):
            self.assertIn(marker, airdrop)

    def test_pins_new_protocol_rulings_and_runtime_mismatch(self):
        data = self.manifest()
        by_id = {source["id"]: source for source in data["sources"]}
        changelog = " | ".join(by_id["yellowpaper_changelog"]["required_markers"])
        for marker in (
            "D-0527",
            "D-0528",
            "D-0529",
            "D-0530",
            "D-0531",
            "sponsored_self_stake_enabled",
            "off-chain explorer referral leaderboard",
            "runtime still burns that leg",
        ):
            self.assertIn(marker, changelog)

        guards = data["interpretation_guards"]
        self.assertEqual(guards["miner_airdrop_unlock"]["testnet_scoring"], "DISTINCT")
        self.assertEqual(guards["miner_airdrop_unlock"]["post_genesis_unlock"],
                         "FINALIZED_MINER_BLOCK_REWARDS_OR_SETTLED_CHANNEL_PAYOUTS")
        self.assertFalse(guards["sponsored_operator_bond"]["enrollment_evidence"])
        self.assertEqual(guards["sponsored_operator_bond"]["self_stake_runtime_flag"],
                         "sponsored_self_stake_enabled")
        self.assertEqual(guards["referral_lottery"]["mode"], "DRAFT_OFF_CHAIN")
        self.assertFalse(guards["referral_lottery"]["eligibility_evidence"])
        self.assertFalse(guards["referral_lottery"]["allocation_evidence"])
        self.assertEqual(guards["failed_early_close_penalty"]["normative_sink"],
                         "FLOPFoundationAccount")
        self.assertEqual(guards["failed_early_close_penalty"]["normative_burn"], "ZERO")
        self.assertEqual(guards["failed_early_close_penalty"]["runtime_status"],
                         "PARTIAL_RUNTIME_STILL_BURNS")

    def test_captured_fixture_matches_committed_baselines_and_markers(self):
        data = self.manifest()
        fixture = json.loads(CAPTURE_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "nanaz.flop-official-criteria-fixture.v1")
        self.assertEqual(fixture["captured_at"], data["captured_at"])
        sources = {source["id"]: source for source in data["sources"]}
        entries = {entry["id"]: entry for entry in fixture["entries"]}
        self.assertEqual(set(entries), set(sources))
        for ident, source in sources.items():
            entry = entries[ident]
            self.assertEqual(entry["url"], source["url"])
            self.assertEqual(criteria_monitor.text_digest(entry["normalized_text"]),
                             entry["normalized_text_sha256"])
            self.assertEqual(entry["normalized_text_sha256"], source["baseline_sha256"])
            for marker in source["required_markers"]:
                self.assertIn(marker, entry["normalized_text"])

    def test_rejects_guard_promotion_or_runtime_mismatch_erasure(self):
        mutations = []
        data = self.manifest()
        data["interpretation_guards"]["sponsored_operator_bond"]["enrollment_evidence"] = True
        mutations.append(data)
        data = self.manifest()
        data["interpretation_guards"]["referral_lottery"]["allocation_evidence"] = True
        mutations.append(data)
        data = self.manifest()
        data["interpretation_guards"]["failed_early_close_penalty"]["runtime_status"] = "COMPLIANT"
        mutations.append(data)
        data = self.manifest()
        data["interpretation_guards"]["miner_airdrop_unlock"]["testnet_scoring"] = "SAME"
        mutations.append(data)
        for mutation in mutations:
            with self.subTest(mutation=mutation["interpretation_guards"]):
                with self.assertRaises(criteria_monitor.ValidationError):
                    criteria_monitor.validate_manifest(mutation)

    def test_rejects_yellowpaper_pin_tampering(self):
        mutations = []
        for field, value in (
            ("commit", "0" * 40),
            ("tree", "0" * 40),
            ("version", "0.5.0"),
            ("status", "FINAL"),
        ):
            data = self.manifest()
            data["yellowpaper_pin"][field] = value
            mutations.append(data)
        for mutation in mutations:
            with self.subTest(mutation=mutation["yellowpaper_pin"]):
                with self.assertRaises(criteria_monitor.ValidationError):
                    criteria_monitor.validate_manifest(mutation)

    def test_marker_removal_is_material_change(self):
        data = self.manifest()
        fetched = self.fetched(data)
        source = data["sources"][0]
        fetched[source["url"]] = fetched[source["url"]].replace(source["required_markers"][0], "removed")
        result = criteria_monitor.evaluate(data, fetched.__getitem__)
        self.assertEqual(result["status"], "material_change")
        self.assertTrue(result["material_changes"])

    def test_hash_drift_with_markers_intact_is_content_change(self):
        data = self.manifest()
        fetched = self.fetched(data)
        fetched[data["sources"][0]["url"]] += " harmless editorial suffix"
        result = criteria_monitor.evaluate(data, fetched.__getitem__)
        self.assertEqual(result["status"], "content_changed")
        self.assertEqual(result["material_changes"], [])

    def test_rejects_unknown_fields_duplicate_urls_and_http(self):
        mutations = []
        data = self.manifest()
        data["unexpected"] = True
        mutations.append(data)
        data = self.manifest()
        data["sources"][1]["url"] = data["sources"][0]["url"]
        mutations.append(data)
        data = self.manifest()
        data["sources"][0]["url"] = "http://example.invalid"
        mutations.append(data)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(criteria_monitor.ValidationError):
                    criteria_monitor.evaluate(mutation, lambda _url: "")

    def test_rejects_missing_or_replaced_required_source_and_conflict(self):
        mutations = []
        data = self.manifest()
        data["sources"][5]["id"] = "replacement"
        data["sources"][5]["url"] = "https://flop.finance/replacement/"
        mutations.append(data)
        data = self.manifest()
        data["sources"][6]["url"] = "https://flop.finance/not-airdrop/"
        mutations.append(data)
        data = self.manifest()
        data["known_conflicts"] = []
        mutations.append(data)
        data = self.manifest()
        data["known_conflicts"][0]["id"] = "replacement_conflict"
        mutations.append(data)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(criteria_monitor.ValidationError):
                    criteria_monitor.validate_manifest(mutation)

    def test_cli_rejects_duplicate_json_keys_normal_and_optimized(self):
        raw = MANIFEST.read_text(encoding="utf-8")
        duplicate = raw.replace(
            '"schema": "nanaz.flop-official-criteria.v3",',
            '"schema": "wrong", "schema": "nanaz.flop-official-criteria.v3",',
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text(duplicate, encoding="utf-8")
            for flags in ([], ["-O"]):
                command = [sys.executable, *flags, str(MODULE), "--manifest", str(path), "--manifest-only"]
                result = subprocess.run(command, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn("duplicate JSON key", result.stderr)

    def test_claims_never_upgrade_allocation(self):
        data = self.manifest()
        data["allocation_status"] = "ELIGIBLE"
        with self.assertRaises(criteria_monitor.ValidationError):
            criteria_monitor.evaluate(data, self.fetched(data).__getitem__)

    def test_cli_fixture_mode_is_deterministic_and_read_only(self):
        before = MANIFEST.read_bytes()
        command = [sys.executable, str(MODULE), "--manifest", str(MANIFEST), "--manifest-only"]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, MANIFEST.read_bytes())

    def test_exit_codes_distinguish_content_and_material_change(self):
        data = self.manifest()
        fetched = self.fetched(data)
        fetched[data["sources"][0]["url"]] += " editorial drift"
        self.assertEqual(criteria_monitor.result_exit_code(criteria_monitor.evaluate(data, fetched.__getitem__)), 2)

        data = self.manifest()
        fetched = self.fetched(data)
        fetched[data["sources"][0]["url"]] = "all markers removed"
        self.assertEqual(criteria_monitor.result_exit_code(criteria_monitor.evaluate(data, fetched.__getitem__)), 3)

    def test_module_has_no_signing_post_or_write_path(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertTrue(calls.isdisjoint({"write", "write_text", "write_bytes", "sign", "send_transaction"}))
        source = MODULE.read_text(encoding="utf-8")
        self.assertNotIn('method="POST"', source)
        self.assertNotIn("private_key", source)
        self.assertNotIn("mnemonic", source)


if __name__ == "__main__":
    unittest.main()
