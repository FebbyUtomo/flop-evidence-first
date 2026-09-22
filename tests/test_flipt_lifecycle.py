import ast
import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "flipt_lifecycle.py"
FIXTURE = ROOT / "evidence" / "fixtures" / "flipt-lifecycle-valid.json"
SPEC = importlib.util.spec_from_file_location("flipt_lifecycle", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load flipt_lifecycle module")
flipt_lifecycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flipt_lifecycle)


class FliptLifecycleTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_valid_public_lifecycle(self):
        result = flipt_lifecycle.validate(self.fixture())
        self.assertEqual(result["chain_id"], 5042002)
        self.assertEqual(result["events"], 6)
        self.assertEqual(result["final_state"], "auto_sell_filled")
        self.assertEqual(result["minimum_maturity_seconds"], 90)

    def test_rejects_wrong_event_order(self):
        data = self.fixture()
        data["events"][4], data["events"][5] = data["events"][5], data["events"][4]
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_release_before_unlock(self):
        data = self.fixture()
        data["events"][2]["timestamp"] = "2026-09-15T09:40:59Z"
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_auto_sell_execution_before_maturity(self):
        data = self.fixture()
        data["events"][5]["timestamp"] = "2026-09-15T10:03:49Z"
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_conditional_exit_misclassification(self):
        data = self.fixture()
        data["events"][4]["action"] = "conditional_exit_created"
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_duplicate_transaction_hash(self):
        data = self.fixture()
        data["events"][5]["tx_hash"] = data["events"][4]["tx_hash"]
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_source_url_hash_mismatch(self):
        data = self.fixture()
        data["events"][0]["source_url"] = data["events"][1]["source_url"]
        with self.assertRaises(flipt_lifecycle.ValidationError):
            flipt_lifecycle.validate(data)

    def test_rejects_wallet_or_balance_material(self):
        for key, value in (
            ("wallet", "creator"),
            ("balance", "1"),
            ("password", "not-a-real-secret"),
            ("api_key", "not-a-real-key"),
            ("executor", "0x" + "12" * 20),
            ("wallet_address", "owner is " + "0x" + "12" * 20),
        ):
            with self.subTest(key=key):
                data = self.fixture()
                data["events"][0][key] = value
                with self.assertRaises(flipt_lifecycle.ValidationError):
                    flipt_lifecycle.validate(data)

    def test_rejects_fractional_maturity_bypass(self):
        for event_index, field in ((1, "unlocks_at"), (4, "matures_at")):
            with self.subTest(event_index=event_index):
                data = self.fixture()
                data["events"][event_index][field] = data["events"][event_index][field].replace("Z", ".900000Z")
                with self.assertRaises(flipt_lifecycle.ValidationError):
                    flipt_lifecycle.validate(data)

    def test_requires_exact_90_second_maturity(self):
        for event_index, field, value in (
            (1, "unlocks_at", "2026-09-15T09:41:02Z"),
            (4, "matures_at", "2026-09-15T10:03:51Z"),
        ):
            with self.subTest(event_index=event_index):
                data = self.fixture()
                data["events"][event_index]["maturity_seconds"] = 91
                data["events"][event_index][field] = value
                with self.assertRaises(flipt_lifecycle.ValidationError):
                    flipt_lifecycle.validate(data)

    def test_rejects_fabricated_semantic_fields(self):
        mutations = (
            (0, "decoded_method", "not_graduate"),
            (1, "amount", {"symbol": "NAKF", "value": "999"}),
            (3, "lp_receipt", {"symbol": "fLP-NAKF", "value": "999"}),
            (4, "tranche_id", 1),
            (4, "keeper_funding", {"symbol": "test-USDC", "value": "999"}),
            (5, "settlement", {"symbol": "test-USDC", "value": "999"}),
        )
        for event_index, field, value in mutations:
            with self.subTest(event_index=event_index, field=field):
                data = self.fixture()
                data["events"][event_index][field] = value
                if field == "tranche_id":
                    data["events"][5]["tranche_id"] = value
                with self.assertRaises(flipt_lifecycle.ValidationError):
                    flipt_lifecycle.validate(data)

    def test_rejects_fabricated_or_unbound_transaction_evidence(self):
        mutations = (
            ("tx_hash", "0x" + "ab" * 32),
            ("method_selector", "0xdeadbeef"),
            ("input_sha256", "ab" * 32),
            ("block_number", 99999999),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                data = self.fixture()
                data["events"][0][field] = value
                if field == "tx_hash":
                    data["events"][0]["source_url"] = (
                        f"https://api-testnet.arc-scan.org/v1/txs/{value}"
                    )
                with self.assertRaises(flipt_lifecycle.ValidationError):
                    flipt_lifecycle.validate(data)

    def test_cli_is_read_only_and_deterministic(self):
        before = FIXTURE.read_bytes()
        command = [sys.executable, str(MODULE), str(FIXTURE)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, FIXTURE.read_bytes())

    def test_module_has_no_network_signing_or_write_path(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertTrue(imported.isdisjoint({"requests", "urllib", "http", "socket", "web3", "nacl"}))
        self.assertTrue(calls.isdisjoint({"open", "write", "write_text", "write_bytes", "send_transaction", "sign"}))


if __name__ == "__main__":
    unittest.main()
