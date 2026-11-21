"""Behaviour tests for classify.py: each test builds a throwaway git repo,
commits risk-tiers.yml on a base branch, commits a change on a PR branch and
runs the script the way the gate does."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("classify.py")
RULES = Path(__file__).resolve().parents[2] / "risk-tiers.yml"


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="classify-"))
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        shutil.copy(RULES, self.repo / "risk-tiers.yml")
        self.write("README.md", "sandbox\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "pr")

    def tearDown(self):
        shutil.rmtree(self.repo)

    def git(self, *args):
        result = run(["git", *args], self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def classify(self, labels="", base="main"):
        env = {**os.environ, "PR_LABELS": labels}
        env.pop("GITHUB_OUTPUT", None)
        env.pop("GITHUB_STEP_SUMMARY", None)
        return run([sys.executable, str(SCRIPT), base, "HEAD"], self.repo, env)

    def assertLane(self, result, lane, code=0):
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertIn(f"Lane: {lane}\n", result.stdout)

    def test_small_docs_change_is_fast(self):
        self.write("docs/setup.md", "Typo fix.\n")
        self.commit("docs")
        self.assertLane(self.classify(), "fast")

    def test_auth_path_is_high_risk(self):
        self.write("src/auth/dryrun_lookup.py", "def find_user(db, name):\n    pass\n")
        self.commit("auth")
        self.assertLane(self.classify(), "high-risk")

    def test_top_level_pii_folder_is_high_risk(self):
        self.write("pii/export.js", "export {};\n")
        self.commit("pii")
        self.assertLane(self.classify(), "high-risk")

    def test_control_file_is_high_risk(self):
        self.write(".github/workflows/x.yml", "on: push\n")
        self.commit("workflow")
        self.assertLane(self.classify(), "high-risk")

    def test_dependency_manifest_is_standard(self):
        self.write("package.json", "{}\n")
        self.commit("deps")
        self.assertLane(self.classify(), "standard")

    def test_more_than_fifty_lines_is_standard(self):
        self.write("docs/long.md", "line\n" * 51)
        self.commit("long docs")
        self.assertLane(self.classify(), "standard")

    def test_fifty_lines_stays_fast(self):
        self.write("docs/long.md", "line\n" * 50)
        self.commit("fifty")
        self.assertLane(self.classify(), "fast")

    def test_lock_file_lines_do_not_count(self):
        self.write("package-lock.json", "x\n" * 900)
        self.write("docs/a.md", "a\n")
        self.commit("lock")
        self.assertLane(self.classify(), "fast")

    def test_over_size_cap_fails_without_label(self):
        self.write("docs/big.md", "line\n" * 500)
        self.commit("big")
        result = self.classify()
        self.assertLane(result, "standard", code=1)
        self.assertIn("size-cap-exception", result.stderr)

    def test_size_cap_label_passes_as_standard(self):
        self.write("docs/big.md", "line\n" * 500)
        self.commit("big")
        self.assertLane(self.classify(labels="size-cap-exception"), "standard")

    def test_label_raises_lane(self):
        self.write("docs/setup.md", "Typo fix.\n")
        self.commit("docs")
        self.assertLane(self.classify(labels="docs,lane:high-risk"), "high-risk")

    def test_label_never_lowers_lane(self):
        self.write("src/auth/session.js", "export {};\n")
        self.commit("auth")
        self.assertLane(self.classify(labels="lane:fast"), "high-risk")

    def test_rules_come_from_base_commit(self):
        rules = (self.repo / "risk-tiers.yml").read_text()
        self.write("risk-tiers.yml", rules.replace('    - "src/auth/*"\n', ""))
        self.write("src/auth/session.js", "export {};\n")
        self.commit("loosen rules and touch auth")
        self.assertLane(self.classify(), "high-risk")

    def test_base_without_rules_file_fails_setup(self):
        self.git("checkout", "-q", "--orphan", "bare")
        self.git("rm", "-q", "-rf", ".")
        self.write("README.md", "no rules\n")
        self.commit("bare base")
        self.git("checkout", "-q", "-b", "pr2")
        self.write("docs/a.md", "a\n")
        self.commit("change")
        result = self.classify(base="bare")
        self.assertEqual(result.returncode, 2)
        self.assertIn("path 'risk-tiers.yml' does not exist", result.stderr)

    def test_writes_lane_to_github_output(self):
        self.write("docs/setup.md", "Typo fix.\n")
        self.commit("docs")
        out = self.repo / "gh-output"
        env = {**os.environ, "PR_LABELS": "", "GITHUB_OUTPUT": str(out)}
        env.pop("GITHUB_STEP_SUMMARY", None)
        result = run([sys.executable, str(SCRIPT), "main", "HEAD"], self.repo, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("lane=fast\n", out.read_text())


if __name__ == "__main__":
    unittest.main()
