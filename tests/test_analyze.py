import json
import tempfile
import unittest
from pathlib import Path

import analyze


class AnalyzeTests(unittest.TestCase):
    def test_summarize_state(self):
        state = {
            "last_seq": 42,
            "claimed": {"a": {"type": "research"}},
            "completed": [
                {"job_id": "k-a", "type": "research", "result_seq": 10,
                 "ts": "2026-01-01T00:00:00Z"},
                {"job_id": "k-b", "type": "build", "result_seq": 11,
                 "ts": "2026-01-02T00:00:00Z"},
            ],
        }
        result = analyze.summarize_state(state)
        self.assertEqual(result["last_seq"], 42)
        self.assertEqual(result["pending_claims"], 1)
        self.assertEqual(result["deliveries"], 2)
        self.assertEqual(result["types"], {"build": 1, "research": 1})
        self.assertEqual(result["first_delivery_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(result["last_delivery_at"], "2026-01-02T00:00:00Z")

    def test_count_campaign_records(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.json").write_text("{}")
            (root / "b.json").write_text("{}")
            self.assertEqual(analyze.count_json_files(root), 2)

    def test_public_output_has_no_private_fields(self):
        public = analyze.build_public_summary(
            {"last_seq": 1, "pending_claims": 0, "deliveries": 1,
             "types": {"review": 1}, "first_delivery_at": "x",
             "last_delivery_at": "y"},
            identity_count=2,
            campaign_post_records=2,
        )
        text = json.dumps(public).lower()
        for forbidden in ("private_key", "passphrase", "seed", "identity.pem", ".tc_pass"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("main_did", public)
        self.assertEqual(public["declared_publication_did"], analyze.MAIN_DID)
        self.assertTrue(
            public["claim_boundaries"]["delivery_sender_did_not_present_in_local_snapshot"]
        )

    def test_audit_identity_records_verifies_did_and_post_record(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            accounts = root / "accounts"
            accounts.mkdir()
            seed = "01" * 32
            key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
            did = analyze.did_from_key(key)
            (accounts / "alice.json").write_text(json.dumps({
                "nickname": "alice", "did": did, "seed": seed
            }))
            audit = analyze.audit_identity_records(accounts, {"alice:lobby": 123})
            self.assertEqual(audit["valid_identity_records"], 1)
            self.assertEqual(audit["did_derivation_matches"], 1)
            self.assertEqual(audit["matched_lobby_post_records"], 1)
            self.assertEqual(audit["invalid_records"], 0)

    def test_summarize_state_reports_unique_valid_deliveries(self):
        state = {
            "last_seq": 9,
            "claimed": {},
            "completed": [
                {"job_id": "k1", "type": "research", "result_seq": 10,
                 "ts": "2026-01-01T00:00:00Z"},
                {"job_id": "k1", "type": "research", "result_seq": 10,
                 "ts": "bad"},
            ],
        }
        result = analyze.summarize_state(state)
        self.assertEqual(result["delivery_records"], 2)
        self.assertEqual(result["valid_delivery_records"], 1)
        self.assertEqual(result["unique_job_ids"], 1)
        self.assertEqual(result["unique_result_sequences"], 1)


if __name__ == "__main__":
    unittest.main()
