import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "contribution_registry.py"
MANIFEST = ROOT / "evidence" / "contributions.json"
SPEC = importlib.util.spec_from_file_location("contribution_registry", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load contribution_registry")
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


class ContributionRegistryTests(unittest.TestCase):
    def data(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_curates_ten_hash_bound_results(self):
        result = registry.validate(self.data(), ROOT)
        self.assertEqual(result["contributions"], 10)
        self.assertEqual(result["result_hashes_verified"], 10)
        self.assertEqual(result["attest"], {"UNVERIFIED": 10, "VERIFIED": 0})
        self.assertEqual(result["accept"], {"UNVERIFIED": 10, "VERIFIED": 0})
        self.assertEqual(result["allocation_status"], "UNVERIFIED")

    def assert_invalid(self, mutate):
        data = self.data()
        mutate(data)
        with self.assertRaises(registry.ValidationError):
            registry.validate(data, ROOT)

    def test_rejects_result_hash_commit_and_url_tampering(self):
        mutations = (
            lambda d: d["contributions"][0]["result"].update(sha256="0" * 64),
            lambda d: d["contributions"][0]["result"].update(commit="deadbeef"),
            lambda d: d["contributions"][0]["result"].update(
                url="https://github.com/FebbyUtomo/flop-evidence-first/blob/main/README.md"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.assert_invalid(mutate)

    def test_rejects_too_few_and_duplicate_results(self):
        self.assert_invalid(lambda d: d.update(contributions=d["contributions"][:9]))
        def duplicate(data):
            data["contributions"][-1]["result"] = copy.deepcopy(
                data["contributions"][0]["result"])
        self.assert_invalid(duplicate)

    def test_unverified_state_cannot_carry_evidence(self):
        self.assert_invalid(lambda d: d["contributions"][0]["attest"].update(
            evidence_url="https://example.org/pretend"))

    def test_verified_state_requires_independent_did_and_https_receipt(self):
        def self_attest(data):
            data["contributions"][0]["attest"] = {
                "status": "VERIFIED", "actor_did": data["primary_did"],
                "evidence_url": "https://example.org/receipt"}
        self.assert_invalid(self_attest)

        def no_receipt(data):
            data["contributions"][0]["accept"] = {
                "status": "VERIFIED", "actor_did": "did:key:z6MkIndependent",
                "evidence_url": None}
        self.assert_invalid(no_receipt)

    def test_allocation_cannot_be_upgraded(self):
        self.assert_invalid(lambda d: d.update(allocation_status="ELIGIBLE"))

    def test_cli_is_deterministic_read_only_and_optimization_safe(self):
        before = MANIFEST.read_bytes()
        command = [sys.executable, str(MODULE), str(MANIFEST)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, "-O", str(MODULE), str(MANIFEST)],
                                   text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout, optimized.stdout)
        self.assertEqual(before, MANIFEST.read_bytes())

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            data = self.data()
            data["contributions"][0]["result"]["path"] = "../outside"
            with self.assertRaises(registry.ValidationError):
                registry.validate(data, Path(td))


if __name__ == "__main__":
    unittest.main()
