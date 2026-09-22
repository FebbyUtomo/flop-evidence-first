import ast

import importlib.util
import json
import subprocess
import sys

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "criteria_monitor.py"
MANIFEST = ROOT / "evidence" / "official-criteria.json"
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
        self.assertEqual(result["sources_checked"], 5)
        self.assertEqual(result["material_changes"], [])
        self.assertEqual(result["allocation_status"], "UNVERIFIED")

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
