import ast
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "receipt_verifier.py"
FIXTURES = ROOT / "evidence" / "fixtures"
PINNED_DID = "did:key:z6MkgjQRmahVjPgCBdoHDPEoUwAMG2KisqjoNDMiH1B68Wcs"
OTHER_DID = "did:key:z6MkokdPbEhPu1GqjPHeN9Zc8mhVkDG8zxqcERLoUWQjEPuf"
SPEC = importlib.util.spec_from_file_location("receipt_verifier", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
receipt_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt_verifier)


class ReceiptVerifierTests(unittest.TestCase):
    def fixture(self, name="technocore-valid.json"):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def assert_invalid(self, receipt, did=PINNED_DID):
        with self.assertRaises(receipt_verifier.VerificationError):
            receipt_verifier.verify_receipt(receipt, did)

    def test_valid_fixture_verifies_against_pinned_did(self):
        result = receipt_verifier.verify_receipt(self.fixture(), PINNED_DID)
        self.assertTrue(result["verified"])
        self.assertEqual(result["from"], PINNED_DID)
        self.assertEqual(result["claim_boundary"], "authorship_and_integrity_only")

    def test_deterministic_negative_fixtures_fail(self):
        for name in (
            "technocore-invalid-text.json",
            "technocore-invalid-signature.json",
            "technocore-wrong-signer.json",
        ):
            with self.subTest(name=name):
                self.assert_invalid(self.fixture(name))

    def test_valid_record_fails_against_different_pinned_did(self):
        self.assert_invalid(self.fixture(), OTHER_DID)

    def test_exact_payload_rejects_whitespace_and_nonce_changes(self):
        for field, value in (("text", "Technocore protocol engagement active. "),
                             ("nonce", 1790042529464)):
            receipt = self.fixture()
            receipt["record"][field] = value
            with self.subTest(field=field):
                self.assert_invalid(receipt)

    def test_rejects_unknown_or_missing_fields(self):
        extra = self.fixture(); extra["network"] = "offline"
        missing = self.fixture(); del missing["record"]["seq"]
        self.assert_invalid(extra)
        self.assert_invalid(missing)

    def test_rejects_malformed_shapes(self):
        mutations = []
        for path, value in (
            (("room",), "Technocore"),
            (("record", "seq"), True),
            (("record", "nonce"), -1),
            (("record", "from"), "did:key:invalid"),
            (("record", "sig"), "A" * 85),
            (("record", "text"), ""),
        ):
            receipt = self.fixture()
            target = receipt
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append(receipt)
        for index, receipt in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_invalid(receipt)

    def test_cli_success_and_failure_exit_codes(self):
        success = subprocess.run(
            [sys.executable, str(MODULE_PATH), str(FIXTURES / "technocore-valid.json"),
             "--did", PINNED_DID], text=True, capture_output=True, check=False)
        failure = subprocess.run(
            [sys.executable, str(MODULE_PATH),
             str(FIXTURES / "technocore-invalid-text.json"), "--did", PINNED_DID],
            text=True, capture_output=True, check=False)
        self.assertEqual(success.returncode, 0)
        self.assertTrue(json.loads(success.stdout)["verified"])
        self.assertEqual(failure.returncode, 1)
        self.assertIn("receipt_invalid", failure.stderr)

    def test_module_has_no_network_private_key_signing_or_write_path(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported_roots = set()
        called_attributes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
        self.assertTrue(imported_roots.isdisjoint(
            {"urllib", "requests", "httpx", "socket", "aiohttp", "paramiko"}))
        self.assertNotIn("Ed25519PrivateKey", MODULE_PATH.read_text(encoding="utf-8"))
        self.assertTrue(called_attributes.isdisjoint(
            {"sign", "write_text", "write_bytes", "open", "urlopen", "request"}))


if __name__ == "__main__":
    unittest.main()
