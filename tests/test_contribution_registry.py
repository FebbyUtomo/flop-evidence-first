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
        self.assertEqual(result["attest"], {"UNVERIFIED": 9, "VERIFIED": 1})
        self.assertEqual(result["accept"], {"UNVERIFIED": 10, "VERIFIED": 0})
        self.assertEqual(result["allocation_status"], "UNVERIFIED")

    def test_roadmap_validator_attest_is_bound_to_public_independent_receipt(self):
        item = next(
            entry for entry in self.data()["contributions"]
            if entry["id"] == "roadmap_integrity_validator"
        )
        attest = item["attest"]
        self.assertEqual(attest["status"], "VERIFIED")
        self.assertEqual(
            attest["actor_did"],
            "did:key:z6MkuzkFDAwgSXgSVhxruVD4DGzuxCieeXonpsgCApd9o6Ms",
        )
        self.assertEqual(
            attest["evidence_url"],
            "https://github.com/FebbyUtomo/flop-evidence-first/issues/1"
            "#issuecomment-6387074008",
        )
        self.assertEqual(attest["receipt"]["snapshot_commit"],
                         "6d931570047ba065a83702083efd08d615da9686")
        self.assertEqual(attest["receipt"]["source_commit"],
                         "f47143668521ede1aee7dc3c37746fb00d9eee24")
        self.assertEqual(attest["receipt"]["contribution_id"],
                         "roadmap_integrity_validator")

    def test_verified_receipt_tampering_is_rejected(self):
        def mutate_receipt(data, mutation):
            item = next(entry for entry in data["contributions"]
                        if entry["id"] == "roadmap_integrity_validator")
            mutation(item["attest"])

        mutations = (
            lambda a: a.update(actor_did="did:key:not-a-valid-multibase-key"),
            lambda a: a.update(evidence_url="https://example.invalid/unrelated"),
            lambda a: a["receipt"].update(receipt_sha256="0" * 64),
            lambda a: a["receipt"].update(transcript_sha256="0" * 64),
            lambda a: a["receipt"].update(mapping_sha256="0" * 64),
            lambda a: a["receipt"].update(contribution_id="offline_quality_gate"),
            lambda a: a["receipt"].update(source_commit="0" * 40),
            lambda a: a["receipt"].update(snapshot_commit="0" * 40),
            lambda a: a["receipt"].update(snapshot_url="https://example.invalid/snapshot"),
            lambda a: a["receipt"].update(
                signature_path=a["receipt"]["receipt_path"],
                signature_sha256=a["receipt"]["receipt_sha256"],
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_invalid(lambda data, m=mutation: mutate_receipt(data, m))

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
