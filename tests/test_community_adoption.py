import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "community_adoption.py"
EVIDENCE = ROOT / "evidence" / "community-adoption.json"
SPEC = importlib.util.spec_from_file_location("community_adoption", MODULE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load community_adoption")
adoption = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adoption)


class CommunityAdoptionTests(unittest.TestCase):
    def data(self):
        return json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_attributable_fork_matches_exact_tutorial(self):
        result = adoption.validate(self.data(), ROOT)
        self.assertEqual(result["adoption"], "VERIFIED_FORK")
        self.assertEqual(result["actor"], "putrikeme")
        self.assertEqual(result["head_commit"], "f31eb692037d68b0cb2089013607230fa32dca95")
        self.assertEqual(result["official_status"], "UNVERIFIED")

    def assert_invalid(self, mutate):
        data = self.data()
        mutate(data)
        with self.assertRaises(adoption.ValidationError):
            adoption.validate(data, ROOT)

    def test_rejects_self_fork_and_weak_independence(self):
        self.assert_invalid(lambda d: d["adoption"].update(actor="FebbyUtomo"))
        self.assert_invalid(lambda d: d["independence_assessment"].update(
            account_has_prior_public_repository_history=False))
        self.assert_invalid(lambda d: d["adoption"].update(actor_public_repositories=0))

    def test_rejects_commit_url_and_content_tampering(self):
        self.assert_invalid(lambda d: d["adoption"].update(head_commit="0" * 40))
        self.assert_invalid(lambda d: d["adoption"].update(
            tutorial_url="https://github.com/putrikeme/flop-evidence-first/blob/main/docs/tutorial-bilingual.md"))
        self.assert_invalid(lambda d: d["adoption"].update(tutorial_sha256="0" * 64))

    def test_official_states_remain_unverified(self):
        for field in self.data()["official_status"]:
            with self.subTest(field=field):
                self.assert_invalid(lambda d, key=field: d["official_status"].update({key: "VERIFIED"}))

    def test_cli_is_deterministic_read_only_and_optimization_safe(self):
        before = EVIDENCE.read_bytes()
        command = [sys.executable, str(MODULE), str(EVIDENCE)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        optimized = subprocess.run([sys.executable, "-O", str(MODULE), str(EVIDENCE)],
                                   text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout, optimized.stdout)
        self.assertEqual(before, EVIDENCE.read_bytes())

    def test_unknown_fields_fail_closed(self):
        data = copy.deepcopy(self.data())
        data["adoption"]["claimed_install"] = True
        with self.assertRaises(adoption.ValidationError):
            adoption.validate(data, ROOT)


if __name__ == "__main__":
    unittest.main()
