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
MODULE = ROOT / "close_call_verifier.py"
PACKAGE = ROOT / "evidence" / "fixtures" / "close-call-official"
SOURCE = ROOT / "evidence" / "close-call-source.json"
SPEC = importlib.util.spec_from_file_location("close_call_verifier", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load close_call_verifier")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class CloseCallVerifierTests(unittest.TestCase):
    def test_pinned_package_and_official_sample_replay(self):
        result = verifier.verify()
        self.assertEqual(result["contest"], "close-1")
        self.assertEqual(result["commit"], verifier.COMMIT)
        self.assertEqual(result["manifest_sha256"], verifier.MANIFEST_SHA256)
        self.assertEqual(result["pinned_artifacts_verified"], 3)
        self.assertEqual(result["sample_sweeps"], 3)
        self.assertEqual(result["sample_owners"], 6)
        self.assertEqual(result["sample_zero_sum"], "0.0000")

    def test_external_lifecycle_never_upgrades(self):
        result = verifier.verify()
        self.assertEqual(result["registration"], "UNVERIFIED")
        self.assertEqual(result["eligibility"], "UNVERIFIED")
        self.assertEqual(result["allocation"], "UNVERIFIED")
        self.assertEqual(result["payment"], "UNVERIFIED")

    def test_rejects_manifest_fold_config_and_sample_tampering(self):
        for relative in ("manifest.json", "close_call_fold.py", "contest.json", "sample-season.jsonl"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                package = Path(directory) / "package"
                shutil.copytree(PACKAGE, package)
                path = package / relative
                path.write_bytes(path.read_bytes() + b"\n")
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify(package, SOURCE)

    def test_rejects_source_pin_and_state_upgrade(self):
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        mutations = []
        changed_hash = copy.deepcopy(source)
        changed_hash["launch_seed"]["package_sha256"] = "0" * 64
        mutations.append(changed_hash)
        upgraded = copy.deepcopy(source)
        upgraded["lifecycle"]["prize_eligible"] = "VERIFIED"
        mutations.append(upgraded)
        for data in mutations:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "source.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify(PACKAGE, path)

    def test_cli_is_deterministic_read_only_and_optimization_safe(self):
        before = {path: path.read_bytes() for path in [SOURCE, *PACKAGE.iterdir()] if path.is_file()}
        command = [sys.executable, str(MODULE)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, "-O", str(MODULE)], text=True,
                                   capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout, optimized.stdout)
        self.assertEqual(before, {path: path.read_bytes() for path in before})


if __name__ == "__main__":
    unittest.main()
