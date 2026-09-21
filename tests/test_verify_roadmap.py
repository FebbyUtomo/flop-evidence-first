import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_roadmap.py"
SPEC = importlib.util.spec_from_file_location("verify_roadmap", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
verify_roadmap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_roadmap)


class RoadmapVerifierTests(unittest.TestCase):
    def fixture(self, root: Path):
        artifact = root / "artifact.md"
        artifact.write_text("evidence", encoding="utf-8")
        artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
        data = {
            "schema": "nanaz.flop-roadmap.v1", "updated_at": "2026-09-21",
            "score": 5, "target": 100, "daily_target_points": 5,
            "allocation_status": "UNVERIFIED",
            "workstreams": [{"id": "evidence", "weight": 100, "score": 5}],
            "completed_tranches": [{
                "id": "evidence_v1", "title": "Evidence package", "workstream": "evidence",
                "date": "2026-09-21", "points": 5,
                "artifacts": [{"path": "artifact.md", "sha256": artifact_hash}],
                "status": "verified",
                "evidence": "A concrete independently checkable evidence statement."
            }],
            "pending_tranches": [],
        }
        roadmap = (
            "| ID | Workstream | Weight | Current | Evidence |\n"
            "|---|---|---:|---:|---|\n"
            "| evidence | Evidence | 100 | 5 | Verified. |\n"
            "| **Total** |  | **100** | **5** | Verified ledger. |\n\n"
            "## Completed evidence ledger — 5 points\n\n"
            "### evidence_v1 — Evidence package (5 points)\n\n"
            "- Workstream: `evidence`\n- Status: `verified`\n"
            f"- Artifact: `artifact.md` — sha256 `{artifact_hash}`\n\n"
            "## Pending evidence ledger — 0 unscored points\n"
        )
        return data, roadmap

    def assert_invalid(self, data, root, roadmap):
        with self.assertRaises(verify_roadmap.ValidationError):
            verify_roadmap.validate(data, root, roadmap)

    def test_valid_scorecard(self):
        with tempfile.TemporaryDirectory() as td:
            data, roadmap = self.fixture(Path(td))
            result = verify_roadmap.validate(data, Path(td), roadmap)
            self.assertEqual(result["score"], 5)

    def test_rejects_nonfinal_tranche(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            data["completed_tranches"][0]["status"] = "pending"
            self.assert_invalid(data, root, roadmap)

    def test_rejects_artifact_path_escape_and_absolute_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            for invalid in ("../outside.md", str((root / "artifact.md").resolve())):
                mutated = copy.deepcopy(data)
                mutated["completed_tranches"][0]["artifacts"][0]["path"] = invalid
                self.assert_invalid(mutated, root, roadmap)

    def test_optimized_python_cannot_bypass_invalid_schema(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root); data["schema"] = "wrong"
            progress = root / "progress.json"; roadmap_file = root / "ROADMAP.md"
            progress.write_text(json.dumps(data)); roadmap_file.write_text(roadmap)
            run = subprocess.run(
                [sys.executable, "-O", str(SCRIPT), "--progress", str(progress),
                 "--roadmap", str(roadmap_file), "--root", str(root)],
                text=True, capture_output=True, check=False)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("roadmap_invalid", run.stderr)

    def test_rejects_markdown_total_and_workstream_divergence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            for mutated in (roadmap.replace("**5**", "**10**"),
                            roadmap.replace("| evidence | Evidence | 100 | 5 |",
                                            "| evidence | Evidence | 100 | 0 |")):
                self.assert_invalid(data, root, mutated)

    def test_rejects_visible_ledger_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            mutations = (
                roadmap.replace("Completed evidence ledger — 5", "Completed evidence ledger — 95"),
                roadmap.replace("Evidence package (5 points)", "Evidence package (50 points)"),
                roadmap.replace("Artifact: `artifact.md`", "Artifact: `missing.md`"),
                roadmap.replace("Workstream: `evidence`", "Workstream: `other`"),
            )
            for mutated in mutations:
                self.assert_invalid(data, root, mutated)

    def test_rejects_conflicting_duplicate_visible_totals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            mutations = (
                "| **Total** |  | **100** | **95** | False. |\n" + roadmap,
                "## Completed evidence ledger — 95 points\n" + roadmap,
                "## Pending evidence ledger — 95 unscored points\n" + roadmap,
            )
            for mutated in mutations:
                self.assert_invalid(data, root, mutated)

    def test_rejects_replayed_or_duplicate_tranche(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            data["completed_tranches"].append(copy.deepcopy(data["completed_tranches"][0]))
            data["score"] = 10; data["workstreams"][0]["score"] = 10
            self.assert_invalid(data, root, roadmap)

    def test_rejects_duplicate_artifact_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            duplicate = copy.deepcopy(data["completed_tranches"][0]); duplicate["id"] = "evidence_v2"
            data["completed_tranches"].append(duplicate)
            data["score"] = 10; data["workstreams"][0]["score"] = 10
            self.assert_invalid(data, root, roadmap)

    def test_rejects_duplicate_content_under_different_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            copied = root / "copy.md"; copied.write_text("evidence")
            duplicate = copy.deepcopy(data["completed_tranches"][0]); duplicate["id"] = "evidence_v2"
            duplicate["title"] = "Copied evidence"
            duplicate["artifacts"][0]["path"] = "copy.md"
            data["completed_tranches"].append(duplicate)
            data["score"] = 10; data["workstreams"][0]["score"] = 10
            self.assert_invalid(data, root, roadmap)

    def test_rejects_wrong_workstream_attribution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            data["workstreams"] = [
                {"id": "evidence", "weight": 50, "score": 0},
                {"id": "other", "weight": 50, "score": 5}]
            self.assert_invalid(data, root, roadmap)

    def test_rejects_artifact_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); data, roadmap = self.fixture(root)
            (root / "artifact.md").write_text("changed")
            self.assert_invalid(data, root, roadmap)


if __name__ == "__main__":
    unittest.main()
