import hashlib
import tempfile
import unittest
from pathlib import Path

import quality_worker


class QualityGateTests(unittest.TestCase):
    def test_rejects_legacy_boilerplate(self):
        job = {"id": "k1", "type": "research", "description": "Verify a public fact from primary sources"}
        draft = {
            "body": "Based on available information, the key points are multiple interconnected factors.",
            "sources": ["https://example.org/a", "https://example.org/b"],
        }
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["approved"])
        self.assertIn("generic_boilerplate", result["reasons"])

    def test_research_requires_two_https_sources(self):
        job = {"id": "k2", "type": "research", "description": "Research a claim with citations"}
        draft = {"body": "A sufficiently detailed original analysis " * 8, "sources": ["https://example.org/a"]}
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["approved"])
        self.assertIn("insufficient_public_sources", result["reasons"])

    def test_build_requires_artifact_and_passing_test(self):
        job = {"id": "k3", "type": "build", "description": "Build and test a parser"}
        draft = {"body": "Implemented a parser with bounded input and explicit errors. " * 5}
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["approved"])
        self.assertIn("missing_artifact", result["reasons"])
        self.assertIn("missing_test_evidence", result["reasons"])

    def test_valid_research_draft_passes_gate_without_approval(self):
        job = {"id": "k4", "type": "research", "description": "Compare two primary records"}
        draft = {
            "body": "The two records differ in scope and reporting date. " * 8,
            "sources": ["https://example.org/a", "https://example.net/b"],
        }
        result = quality_worker.evaluate(job, draft)
        self.assertTrue(result["gate_passed"])
        self.assertFalse(result["approved"])
        self.assertEqual(result["mode"], "offline_only")
        self.assertFalse(result["can_publish"])

    def test_private_or_credentialed_source_urls_are_rejected(self):
        job = {"id": "k6", "type": "research", "description": "Research a public claim with citations"}
        draft = {
            "body": "Specific analysis with enough detail for structural review. " * 8,
            "sources": [
                "https://user:pass@example.org/a",
                "https://" + ".".join(["127", "0", "0", "1"]) + "/private",
            ],
        }
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["gate_passed"])
        self.assertIn("insufficient_public_sources", result["reasons"])

    def test_claimed_test_result_never_becomes_publish_approval(self):
        job = {"id": "k7", "type": "build", "description": "Build and test a parser"}
        draft = {
            "body": "Implemented a parser with bounded input and explicit errors. " * 5,
            "artifact": "does-not-exist.py",
            "tests": {"passed": True, "command": "pretend-test"},
        }
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["gate_passed"])
        self.assertFalse(result["approved"])
        self.assertIn("artifact_not_verified", result["reasons"])

    def test_build_with_forged_test_receipt_requires_manual_execution_review(self):
        job = {"id": "k9", "type": "build", "description": "Build and test a parser"}
        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / "unrelated.txt"
            artifact.write_text("unrelated")
            draft = {
                "body": "Implemented a parser with bounded input and explicit errors. " * 5,
                "artifact": {
                    "path": str(artifact),
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                },
                "tests": {"command": "false", "exit_code": 0, "output_sha256": "0" * 64},
            }
            result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["gate_passed"])
        self.assertIn("build_requires_manual_execution_review", result["reasons"])

    def test_host_paths_and_email_are_sensitive(self):
        job = {"id": "k8", "type": "explain", "description": "Explain a deployment incident safely"}
        draft = {"body": ("Contact admin@example.org and inspect /" + "root/private/config. ") * 5}
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["gate_passed"])
        self.assertIn("sensitive_content", result["reasons"])

    def test_secret_shape_is_rejected(self):
        job = {"id": "k5", "type": "explain", "description": "Explain safe secret handling"}
        draft = {"body": "Use this credential: " + "s" + "k" + "-" + ("a" * 32)}
        result = quality_worker.evaluate(job, draft)
        self.assertFalse(result["approved"])
        self.assertIn("sensitive_content", result["reasons"])

    def test_common_cloud_chat_and_jwt_credentials_are_rejected(self):
        job = {"id": "k10", "type": "explain", "description": "Explain safe credential handling"}
        credentials = [
            "A" + "KIA" + ("A" * 16),
            "x" + "oxb-" + ("1" * 12) + "-" + ("2" * 12) + "-" + ("a" * 24),
            ("a" * 24) + "." + ("b" * 24) + "." + ("c" * 24),
        ]
        for credential in credentials:
            with self.subTest(credential_type=credential[:4]):
                draft = {"body": ("Potential leaked credential: " + credential + ". ") * 5}
                result = quality_worker.evaluate(job, draft)
                self.assertFalse(result["gate_passed"])
                self.assertIn("sensitive_content", result["reasons"])


if __name__ == "__main__":
    unittest.main()
