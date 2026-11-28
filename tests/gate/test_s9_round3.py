"""Gate test for slice S9, round 3 (laravel-layer): gate-commit matching, renames, optional locks, PR base.

Contract: tests/Agents/CONTRACT-S9.md section 8. Where a fact is about git behaviour, a real temp-repo
test shows it; the agent-text tests then check that the agents follow the safe method.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402

I_S = re.I | re.S
REVIEWERS = ("laravel-reviewer", "laravel-reviewer-deep")
GATE_USERS = ("laravel-reviewer", "laravel-reviewer-deep", "laravel-builder", "laravel-debugger")
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
       "GIT_AUTHOR_NAME": "f", "GIT_AUTHOR_EMAIL": "f@example.invalid",
       "GIT_COMMITTER_NAME": "f", "GIT_COMMITTER_EMAIL": "f@example.invalid"}


def body(test, stem):
    return s8.read_agent(test, stem)


def check_all(test, stems, rules):
    for stem in stems:
        text = body(test, stem)
        for label, pattern in rules:
            with test.subTest(agent=stem, rule=label):
                test.assertRegex(text, re.compile(pattern, I_S), f"{stem} does not state: {label}")


class Repo:
    def __init__(self, test: unittest.TestCase, bare_name: str = "repo"):
        self.dir = Path(tempfile.mkdtemp(prefix="lcs-s9r3-"))
        test.addCleanup(shutil.rmtree, self.dir, True)
        self.path = self.dir / bare_name
        self.path.mkdir()
        self.git("init", "-q", "-b", "main")

    def git(self, *a, check=True, env=None, cwd=None):
        return subprocess.run(["git", *a], cwd=cwd or self.path, capture_output=True, text=True, check=check, env=env or ENV)

    def write(self, rel, text="1"):
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, msg, *args):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, *args)
        return self.git("rev-parse", "HEAD").stdout.strip()


def subject_matches(repo: Repo, slice_id: str) -> list:
    """The safe method: subjects only, compared as strings."""
    out = []
    for line in repo.git("log", "--format=%H %s").stdout.splitlines():
        sha, subject = line.split(" ", 1)
        if subject == f"test(gate): {slice_id}" or subject.startswith(f"test(gate): {slice_id} "):
            out.append(sha)
    return out


class GitFacts(unittest.TestCase):
    def test_a_body_line_or_a_regex_slice_id_makes_grep_over_match_and_the_subject_method_does_not(self):
        r = Repo(self)
        r.write("README"); r.commit("base")
        r.write("tests/AKTest.php"); real = r.commit("test(gate): AK-S1")
        r.write("src/x.php"); r.commit("feat: x", "-m", "test(gate): AK-S1")  # body line only
        grep = r.git("log", "--grep", "^test(gate): AK-S1", "--format=%H").stdout.split()
        self.assertEqual(len(grep), 2, "--grep matches the body line: a feature commit becomes a gate commit")
        self.assertEqual(subject_matches(r, "AK-S1"), [real])
        self.assertEqual(subject_matches(r, "AK-S."), [], "a slice id is a string, not a regex: AK-S. is not AK-S1")
        wild = r.git("log", "--grep", "^test(gate): AK-S.", "--format=%H").stdout.split()
        self.assertTrue(wild, "as a raw regex AK-S. would have matched")

    def test_renames_attribute_the_old_path_to_the_earlier_commit_unless_listed_without_renames(self):
        r = Repo(self)
        r.write("README"); r.commit("base")
        r.write("tests/A.php", "x" * 200); first = r.commit("test(gate): S1")
        (r.path / "tests/A.php").rename(r.path / "tests/B.php")
        second = r.commit("test(gate): S1 round 2")
        default = r.git("show", "--name-only", "--format=", second).stdout.split()
        self.assertEqual(default, ["tests/B.php"], "with rename detection the old path is not listed at all")
        status = r.git("show", "--name-status", "--no-renames", "--format=", second).stdout.splitlines()
        self.assertEqual(sorted(l.split("\t") [0] + ":" + l.split("\t")[1] for l in status), ["A:tests/B.php", "D:tests/A.php"])
        # tests/A.php was deleted by the later gate commit: it is not a gate file at the tip.
        self.assertFalse((r.path / "tests/A.php").exists())
        self.assertEqual(r.git("cat-file", "-e", f"{first}:tests/A.php", check=False).returncode, 0, "it did exist in the first commit")
        self.assertNotEqual(r.git("cat-file", "-e", "HEAD:tests/A.php", check=False).returncode, 0)

    def test_optional_locks_zero_leaves_the_index_alone(self):
        r = Repo(self)
        r.write("tests/T.php"); r.commit("base")
        index = r.path / ".git/index"

        def touch_and_status(env):
            p = r.path / "tests/T.php"
            os.utime(p, (time.time() + 5, time.time() + 5))  # stat-dirty, content identical
            before = index.read_bytes()
            r.git("status", "--porcelain", "-uall", env=env)
            return index.read_bytes() != before

        plain = {k: v for k, v in ENV.items() if k != "GIT_OPTIONAL_LOCKS"}  # an exported value must not leak in
        self.assertTrue(touch_and_status(plain), "a plain git status refreshes (writes) the index")
        self.assertFalse(touch_and_status({**plain, "GIT_OPTIONAL_LOCKS": "0"}), "GIT_OPTIONAL_LOCKS=0 does not")

    def test_a_stale_local_base_differs_from_the_fetched_remote_base(self):
        origin = Repo(self, "origin")
        origin.write("README"); origin.commit("base")
        clone = origin.dir / "clone"
        subprocess.run(["git", "clone", "-q", str(origin.path), str(clone)], check=True, env=ENV, capture_output=True)
        origin.write("tests/New.php"); new = origin.commit("test(gate): S1 on main")
        subprocess.run(["git", "fetch", "-q", "origin"], cwd=clone, check=True, env=ENV, capture_output=True)
        local = subprocess.run(["git", "rev-parse", "main"], cwd=clone, capture_output=True, text=True, env=ENV).stdout.strip()
        remote = subprocess.run(["git", "rev-parse", "origin/main"], cwd=clone, capture_output=True, text=True, env=ENV).stdout.strip()
        self.assertNotEqual(local, remote, "the local main is stale; origin/main is the base after a fetch")
        self.assertEqual(remote, new)


class SubjectOnlyMatching(unittest.TestCase):
    """Ruling 1."""

    RULES = [
        ("lists commits with %H %s", r"git log --format='%H %s'"),
        ("gate commits are matched on the subject only", r"subject (line )?only|only (on )?the subject|subjects? only"),
        ("a body line does not make a gate commit", r"body[^.]{0,200}(not|never)[^.]{0,120}(gate commit|match)"),
        ("the slice id is compared literally, or escaped", r"(compared|compare)[^.]{0,80}(literal|as a string)[^.]{0,200}(never|not)[^.]{0,60}regex|escape[^.]{0,60}slice id|slice id[^.]{0,120}escape"),
    ]

    def test_every_gate_user_matches_subjects_literally(self):
        check_all(self, GATE_USERS, self.RULES)

    def test_the_old_grep_form_is_no_longer_the_way_to_find_gate_commits(self):
        for stem in GATE_USERS:
            with self.subTest(agent=stem):
                self.assertNotRegex(body(self, stem), r"git log --grep ['\"]\^test\(gate\):[^`\n]*<slice[^`\n]*>",
                                    "--grep with the slice id as a regex also matches body lines")


class RenamesAndDeletions(unittest.TestCase):
    """Ruling 2."""

    RULES = [
        ("lists gate files without rename detection", r"--no-renames|--name-status"),
        ("a renamed file's old path is not attributed to the earlier commit", r"renam\w+[^.]{0,300}(old path|earlier (gate )?commit)"),
        ("each file is checked against the last gate commit that touched it", r"last gate commit that touched"),
        ("only where the file exists in that commit", r"(file )?exists? in (that|the) (gate )?commit|in which the file exists"),
        ("a file a later gate commit deleted is not a gate file", r"(later|last) gate commit[^.]{0,120}delet\w+[^.]{0,200}not a gate file"),
    ]

    def test_every_gate_user_handles_renames_and_deletions(self):
        check_all(self, GATE_USERS, self.RULES)


class OptionalLocks(unittest.TestCase):
    """Ruling 3."""

    def test_both_reviewers_set_optional_locks_for_every_git_command(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertIn("GIT_OPTIONAL_LOCKS=0", text)
                self.assertRegex(text, re.compile(r"GIT_OPTIONAL_LOCKS=0[^.]{0,300}(every|all) git (command|call)|(every|all) git (command|call)[^.]{0,300}GIT_OPTIONAL_LOCKS=0", I_S))
                for cmd in ("status", "diff", "ls-files", "log"):
                    self.assertRegex(text, re.compile(rf"GIT_OPTIONAL_LOCKS=0[^.\n]{{0,400}}{cmd}|{cmd}[^.\n]{{0,400}}GIT_OPTIONAL_LOCKS=0", I_S), cmd)


class PrBase(unittest.TestCase):
    """Ruling 4."""

    def test_the_pr_base_is_the_remote_after_a_fetch_or_the_merge_base(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertIn("origin/<baseRefName>", text)
                self.assertRegex(text, re.compile(r"fetch[^.]{0,200}origin/<baseRefName>|origin/<baseRefName>[^.]{0,200}fetch", I_S))
                self.assertRegex(text, re.compile(r"merge[- ]base", I_S))
                self.assertRegex(text, re.compile(r"(never|not)[^.]{0,80}(stale )?local (base )?branch|local branch[^.]{0,80}stale", I_S))


class ExcludedCommits(unittest.TestCase):
    """Ruling 5."""

    def test_a_gate_commit_the_brief_excludes_is_reported_never_used(self):
        for stem in GATE_USERS:
            with self.subTest(agent=stem):
                self.assertRegex(body(self, stem), re.compile(r"(brief|caller)[^.]{0,120}exclud\w+[^.]{0,300}report\w*[^.]{0,200}never (used|use)", I_S))


class DeepChallengeRound3(unittest.TestCase):
    """Rulings 6 and 7."""

    def body(self):
        return body(self, "laravel-reviewer-deep")

    def test_no_challenger_when_every_serious_finding_is_deterministic(self):
        text = self.body()
        self.assertIn("Challenge: none (all findings deterministic)", text)
        self.assertRegex(text, re.compile(r"every Critical (and|or) Important finding is deterministic[^.]{0,300}(no|not|never)[^.]{0,60}(challenger|challenge)", I_S))

    def test_phpstan_cache_writes_are_the_one_stated_exception_to_no_file_writes(self):
        text = self.body()
        self.assertRegex(text, re.compile(r"phpstan[^.]{0,120}cache[^.]{0,300}(exception|allowed)[^.]{0,200}file writes|file writes[^.]{0,300}(except|exception)[^.]{0,200}phpstan[^.]{0,120}cache", I_S))
        self.assertRegex(text, re.compile(r"(the )?(one|only|single) exception", I_S))


if __name__ == "__main__":
    unittest.main()
