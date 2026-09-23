import ast
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "sonnet_results_verifier.py"
PACKAGE = ROOT / "evidence" / "fixtures" / "sonnet-2-official"
SOURCE = ROOT / "evidence" / "sonnet-2-source.json"
NEGATIVE_CASES = ROOT / "evidence" / "fixtures" / "sonnet-2-negative-cases.json"
PRIMARY_RECEIPT = ROOT / "evidence" / "technocore-receipt.json"
SPEC = importlib.util.spec_from_file_location("sonnet_results_verifier", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class SonnetResultsVerifierTests(unittest.TestCase):
    def source(self):
        return json.loads(SOURCE.read_text(encoding="utf-8"))

    def listed_did(self):
        payouts = json.loads((PACKAGE / "payouts.json").read_text(encoding="utf-8"))
        return next(iter(payouts))

    def test_official_fixture_and_listed_exact_did_verify(self):
        result = verifier.verify_package(PACKAGE, self.source(), self.listed_did())
        self.assertTrue(result["package_verified"])
        self.assertEqual(result["official_commit"], verifier.OFFICIAL_COMMIT)
        self.assertEqual(result["recipients_verified"], 6856)
        self.assertEqual(result["allocated_total_verified"], 97964)
        self.assertEqual(result["allocation"]["status"], "LISTED")
        self.assertIn(result["allocation"]["amount_flop"], {7, 12500})

    def test_primary_did_is_not_listed_and_lifecycle_stays_unverified(self):
        primary_did = json.loads(PRIMARY_RECEIPT.read_text(encoding="utf-8"))["from"]
        result = verifier.verify_package(PACKAGE, self.source(), primary_did)
        self.assertEqual(result["allocation"], {"status": "NOT_LISTED"})
        self.assertEqual(result["claimable"]["status"], "UNVERIFIED")
        self.assertEqual(result["claimed"]["status"], "UNVERIFIED")
        self.assertEqual(result["paid"]["status"], "UNVERIFIED")
        self.assertNotIn(primary_did, json.dumps(result))

    def test_declared_negative_fixtures_fail_closed(self):
        fixture = json.loads(NEGATIVE_CASES.read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "nanaz.sonnet-2-negative-cases.v1")
        self.assertEqual(len(fixture["cases"]), 4)
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as td:
                package = Path(td) / "package"
                shutil.copytree(PACKAGE, package)
                source = self.source()
                if case["operation"] == "replace_sha256":
                    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
                    manifest["sha256"]["standings.json"] = "0" * 64
                    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                elif case["operation"] == "replace_first_amount":
                    path = package / case["target"]
                    text = path.read_text(encoding="utf-8")
                    if path.suffix == ".json":
                        payouts = json.loads(text)
                        payouts[next(iter(payouts))] = 8
                        path.write_text(json.dumps(payouts, separators=(",", ":")), encoding="utf-8")
                    else:
                        path.write_text(text.replace(",12500,", ",12501,", 1), encoding="utf-8")
                elif case["operation"] == "replace_commit":
                    source["official_commit"] = "0" * 40
                else:
                    self.fail(f"unknown fixture operation: {case['operation']}")
                with self.assertRaisesRegex(verifier.VerificationError, case["expected_error"]):
                    verifier.verify_package(package, source, self.listed_did())

    def test_manifest_still_rejects_tamper_if_source_hash_is_rebased(self):
        with tempfile.TemporaryDirectory() as td:
            package = Path(td) / "package"
            shutil.copytree(PACKAGE, package)
            path = package / "payouts.json"
            payouts = json.loads(path.read_text(encoding="utf-8"))
            payouts[next(iter(payouts))] = 8
            path.write_text(json.dumps(payouts, separators=(",", ":")), encoding="utf-8")
            source = self.source()
            source["package_files"]["payouts.json"] = verifier.digest(path)
            with self.assertRaisesRegex(verifier.VerificationError, "manifest hash mismatch: payouts.json"):
                verifier.verify_package(package, source, self.listed_did())

    def test_rejects_malformed_lookup_did(self):
        with self.assertRaisesRegex(verifier.VerificationError, "canonical Ed25519"):
            verifier.verify_package(PACKAGE, self.source(), "did:key:not-valid")

    def test_cli_is_deterministic_and_does_not_echo_lookup_did(self):
        did = self.listed_did()
        command = [
            sys.executable, str(MODULE_PATH), str(PACKAGE),
            "--source-record", str(SOURCE), "--did", did,
        ]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertNotIn(did, first.stdout)
        self.assertTrue(json.loads(first.stdout)["package_verified"])

    def test_module_has_no_network_private_key_signing_claim_or_write_path(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots = set()
        called_attributes = set()
        called_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    called_attributes.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
        self.assertTrue(imported_roots.isdisjoint(
            {"urllib", "requests", "httpx", "socket", "aiohttp", "web3", "solana"}))
        self.assertTrue(called_attributes.isdisjoint(
            {"write", "write_text", "write_bytes", "sign", "send_transaction", "urlopen", "request"}))
        self.assertTrue(called_names.isdisjoint({"open", "sign", "claim"}))
        self.assertNotIn("private_key", source)
        self.assertNotIn("mnemonic", source)
        self.assertNotIn('method="POST"', source)


if __name__ == "__main__":
    unittest.main()
