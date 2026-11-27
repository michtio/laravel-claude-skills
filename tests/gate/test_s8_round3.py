"""Gate test for slice S8, round 3 (laravel-layer): revert-to-prove without the stash, sizing,
runner precedence and nits; plus the fixture-app lock.

Contract: tests/Agents/CONTRACT.md section 6. Each test states behaviour a real agent must
follow and checks that its text carries it. Run from tests/gate or through discover.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import test_s8 as s8

REPO = s8.REPO
I_S = re.I | re.S
MISSING_REGISTER = (r"(?is)(missing|not installed|cannot load|not available)[^.]{0,200}register.{0,400}no verdict|"
                    r"register[^.]{0,200}(missing|not installed|cannot load|not available).{0,400}no verdict")


def text(test, stem):
    return s8.read_agent(test, stem)


class RevertToProve(unittest.TestCase):
    def body(self):
        return text(self, "laravel-builder")

    def test_proof_copies_reverts_in_the_working_tree_only_and_restores_from_the_copies(self):
        b = self.body()
        self.assertRegex(b, r"(?is)cop(y|ies)[^.]{0,160}(temp|temporary)[^.]{0,120}outside the repo")
        self.assertIn("git show <base>:<path> > <path>", b)
        self.assertRegex(b, r"(?is)(new in the slice|added by the slice|new files?)[^.]{0,120}(delete|remove)")
        self.assertRegex(b, r"(?is)red.{0,600}restore[^.]{0,120}cop(y|ies).{0,400}\bcmp\b.{0,400}green")

    def test_proof_never_uses_stash_checkout_restore_or_add(self):
        b = self.body()
        lines = [l for l in b.splitlines() if re.search(r"(?i)\bnever\b", l)]
        ok = [l for l in lines if all(t in l for t in ("git stash", "git checkout -- <files>", "git restore", "git add"))]
        self.assertTrue(ok, "no line says the proof never runs git stash, git checkout -- <files>, git restore or git add")
        self.assertNotRegex(b, r"git stash push", "the proof must not stash")
        self.assertNotIn("git checkout <base> -- <files>", b)
        self.assertNotRegex(b, r"(?i)only stash")

    def test_base_is_defined(self):
        self.assertRegex(self.body(), r"(?is)<base>[^.]{0,120}(is|means)[^.]{0,120}gate commit[^.]{0,200}(otherwise|else)[^.]{0,160}(started from|start(ed)? )")

    def test_a_failed_step_restores_confirms_and_stops(self):
        b = self.body()
        self.assertRegex(b, r"(?is)(any|if a|if any) step fails?[^.]{0,200}restor[^.]{0,160}cop(y|ies)[^.]{0,160}\bcmp\b[^.]{0,160}(stop|report)")
        self.assertRegex(b, r"(?is)no step leaves the fix outside the working tree")

    def test_a_test_that_stays_green_is_handled_by_its_owner(self):
        b = self.body()
        self.assertRegex(b, r"(?is)stays green[^.]{0,200}gate test[^.]{0,200}(finding|report)[^.]{0,120}owner[^.]{0,160}never edit")
        self.assertRegex(b, r"(?is)(test you wrote|your own test|a test (you|it) wrote)[^.]{0,200}rewrite[^.]{0,120}(fails?|red) without the fix")

    def test_revert_to_prove_runs_last(self):
        b = self.body()
        self.assertRegex(b, r"(?is)revert-to-prove[^.]{0,200}\blast\b|\blast\b[^.]{0,120}revert-to-prove")
        self.assertRegex(b, r"(?is)after[^.]{0,120}simplification pass")
        self.assertRegex(b, r"(?is)after[^.]{0,200}(fixes? (from|after) the checker|checker fixes|fixes? the checker)")
        self.assertRegex(b, r"(?is)(final|last) code")

    def test_g8_wording_is_kept_and_the_reference_does_not_name_stash(self):
        self.assertRegex(self.body(), r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted")
        ref = s8.REFERENCE_RULES
        if not ref.is_file():
            self.skipTest("GATE_DISCIPLINE_RULES is not set")
        g8 = [l for l in ref.read_text(encoding="utf-8").splitlines() if l.startswith("G8\t")]
        self.assertTrue(g8)
        self.assertFalse(any("stash" in l.lower() for l in g8), "the reference's G8 row names stash")


class Sizing(unittest.TestCase):
    def test_builder_counts_untracked_files(self):
        b = text(self, "laravel-builder")
        self.assertRegex(b, r"(?is)untracked[^.]{0,300}(git add -N|intent to add|git status --porcelain)|(git add -N|git status --porcelain)[^.]{0,300}untracked")
        self.assertIn("git add -N", b)
        self.assertRegex(b, r"(?is)git add -N.{0,200}git diff --numstat <base>|git diff --numstat <base>.{0,200}git add -N|before[^.]{0,80}git diff --numstat")

    def test_checker_diffs_the_working_tree_against_base_when_uncommitted(self):
        c = text(self, "laravel-review-checker")
        self.assertRegex(c, r"(?is)uncommitted[^.]{0,300}git diff <base>|git diff <base>[^.]{0,300}uncommitted")
        self.assertRegex(c, r"(?is)never[^.]{0,80}three-dot|three-dot[^.]{0,120}never")

    def test_builder_hands_the_checker_the_right_diff_command(self):
        self.assertRegex(text(self, "laravel-builder"), r"(?is)uncommitted[^.]{0,300}git diff <base>(?!\.\.\.)|git diff <base>(?!\.\.\.)[^.]{0,300}uncommitted")


class Nits(unittest.TestCase):
    def test_planner_runner_beats_ddev_detection(self):
        self.assertRegex(text(self, "laravel-planner"),
                         r"(?is)(explicit|profile)[^.]{0,80}runner[^.]{0,200}(wins|takes precedence|overrides|beats)[^.]{0,200}(detect|\.ddev)")

    def test_build_section_is_test_first(self):
        b = text(self, "laravel-builder")
        self.assertNotRegex(b, r"(?i)code and its tests together")
        build = b[b.index("## Build"):b.index("**Fix rounds")]
        self.assertRegex(build, r"(?is)test[^.]{0,80}(before|first)[^.]{0,80}(its |the )?(code|layer)|(before|first)[^.]{0,60}(its |the )?code[^.]{0,80}test")

    def test_gate_writer_has_the_testbench_caveat(self):
        g = text(self, "laravel-gate-writer")
        self.assertRegex(g, r"(?is)testbench[^.]{0,300}(in-memory|:memory:)|(in-memory|:memory:)[^.]{0,300}testbench")

    def test_builder_says_a_filter_matching_no_tests_is_not_red(self):
        self.assertRegex(text(self, "laravel-builder"), r"(?is)(No tests found|(filter )?match(es|ing)? no tests?)[^.]{0,250}\bnot\b[^.]{0,80}red")

    def test_checker_reports_a_missing_register(self):
        c = text(self, "laravel-review-checker")
        self.assertRegex(c, MISSING_REGISTER)
        self.assertRegex(c, r"(?is)report[^.]{0,200}(missing|not installed|cannot load)|(missing|not installed|cannot load)[^.]{0,200}report")

    def test_isolation_needs_a_pinned_name_that_differs_from_the_dev_database(self):
        for stem in ("laravel-builder", "laravel-gate-writer"):
            with self.subTest(agent=stem):
                t = text(self, stem)
                self.assertRegex(t, r"(?is)(differ(s|ent)? from|not (the )?same as)[^.]{0,200}(dev(elopment)? database|dev database name|\.env)")
                self.assertRegex(t, r"(?is)\.env[^.]{0,300}ddev|ddev[^.]{0,300}\.env")


class FixtureAppLock(unittest.TestCase):
    """The reviewer saw `ddev-lcs-fixture-app-web` already in use and a SIGTERM during boost:update.
    The fixture tests share one DDEV project and never serialised against a second run."""

    def test_the_lock_serialises_two_holders_and_dies_with_its_holder(self):
        import ddev_lock
        first = ddev_lock.acquire(timeout=5)
        try:
            with self.assertRaises(TimeoutError):
                ddev_lock.acquire(timeout=0.3, poll=0.05)
            code = "import sys; sys.path.insert(0, %r); import ddev_lock; ddev_lock.acquire(timeout=0.3, poll=0.05)" % str(Path(__file__).parent)
            other = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
            self.assertNotEqual(other.returncode, 0, "a second process got the lock")
            self.assertIn("TimeoutError", other.stderr)
        finally:
            ddev_lock.release(first)
        again = ddev_lock.acquire(timeout=2)
        ddev_lock.release(again)

    def test_every_class_that_uses_the_fixture_app_takes_the_lock(self):
        for file, cls in (("test_s5.py", "FixtureAppIntegration"), ("test_s6a.py", "RunnerGuidanceSurvivesBoostUpdate"),
                          ("test_s6b.py", "AppIsolationInDdev"), ("test_s6b.py", "AppIsolationOnPostgresInDdev")):
            src = (Path(__file__).parent / file).read_text()
            body = src[src.index(f"class {cls}("):]
            setup = body[body.index("def setUpClass"):][:400]
            with self.subTest(cls=cls):
                self.assertIn("ddev_lock.acquire()", setup)
                self.assertIn("addClassCleanup(ddev_lock.release", setup)


if __name__ == "__main__":
    unittest.main()
