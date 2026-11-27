"""Gate test for slice S9, round 2 (laravel-layer): procedural holes found when the reviewer ran on a real PR.

Contract: tests/Agents/CONTRACT-S9.md section 7. Each test states behaviour a real agent must follow and
checks that the agent's text carries it. What a model does with the text is the release runner's job (S11).
Run: python3 -m unittest discover -s tests/gate   (or python3 -m unittest tests.gate.test_s9_round2)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
import test_s9 as s9  # noqa: E402

I_S = re.I | re.S
REVIEWERS = ("laravel-reviewer", "laravel-reviewer-deep")
GATE_USERS = ("laravel-reviewer", "laravel-reviewer-deep", "laravel-builder", "laravel-debugger")


def body(test, stem):
    return s8.read_agent(test, stem)


def check_all(test, stems, rules):
    for stem in stems:
        text = body(test, stem)
        for label, pattern in rules:
            with test.subTest(agent=stem, rule=label):
                test.assertRegex(text, re.compile(pattern, I_S), f"{stem} does not state: {label}")


class SeveralGateCommits(unittest.TestCase):
    """Ruling 1: a slice can have several gate commits (reviewer, deep reviewer, builder, debugger)."""

    RULES = [
        ("a slice can have several gate commits", r"(several|more than one|multiple)[^.]{0,80}gate commits?"),
        ("the gate files are the union of every gate commit", r"union"),
        ("found in <base>..HEAD", r"<base>\.\.HEAD"),
        ("a gate commit is one whose message names the slice", r"messages? names? the slice|names? the slice"),
        ("commits the brief or caller names win", r"(brief|caller)[^.]{0,160}names?[^.]{0,240}(win|wins|take precedence|instead|only)"),
        ("a forged late gate commit must not redefine the gate", r"forged|a later[^.]{0,80}test\(gate\):[^.]{0,240}(not|never)[^.]{0,60}(redefine|define|widen|change)"),
        ("each gate commit is lock-checked, in both forms", r"each gate commit[^.]{0,400}(both forms|both)"),
        ("literal paths: :(literal) or a per-path existence check", r":\(literal\)|per-path existence|git cat-file -e|git ls-tree"),
        ("exit 128 is an error to report", r"\b128\b[^.]{0,300}error"),
        ("exit 128 is never a pass", r"\b128\b[^.]{0,300}(never|not)[^.]{0,80}(as )?(a )?pass|(never|not)[^.]{0,80}(as )?a pass[^.]{0,200}\b128\b"),
    ]

    def test_every_agent_that_uses_gate_files_carries_the_multi_commit_rule(self):
        check_all(self, GATE_USERS, self.RULES)

    def test_the_builder_no_longer_assumes_one_gate_commit_for_a_supplied_flow(self):
        text = body(self, "laravel-builder")
        self.assertRegex(text, re.compile(r"(several|more than one|multiple)[^.]{0,120}gate commits?[^.]{0,400}(supplied|caller|round)|"
                                          r"(supplied|caller)[^.]{0,200}gate commits?[^.]{0,300}(several|more than one|multiple)", I_S))

    def test_git_facts_the_rule_rests_on(self):
        # Why a per-path existence check and why 128 is not a pass: a path that exists nowhere compares clean
        # (exit 0); a bad revision exits 128.
        tmp = Path(tempfile.mkdtemp(prefix="lcs-s9r2-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
               "GIT_AUTHOR_NAME": "f", "GIT_AUTHOR_EMAIL": "f@example.invalid",
               "GIT_COMMITTER_NAME": "f", "GIT_COMMITTER_EMAIL": "f@example.invalid"}

        def git(*a, check=True):
            return subprocess.run(["git", *a], cwd=tmp, capture_output=True, text=True, check=check, env=env)

        git("init", "-q")
        (tmp / "tests").mkdir()
        (tmp / "README").write_text("x")
        git("add", "."); git("commit", "-qm", "base")
        (tmp / "tests/[a]Test.php").write_text("1")
        git("add", "."); git("commit", "-qm", "test(gate): S1")
        gate1 = git("rev-parse", "HEAD").stdout.strip()
        (tmp / "tests/BTest.php").write_text("1")
        git("add", "."); git("commit", "-qm", "test(gate): S1 round 2")
        (tmp / "tests/CTest.php").write_text("1")
        git("add", "."); git("commit", "-qm", "test(gate): S2")
        names = git("log", "--grep", "^test(gate): S1", "--name-only", "--format=").stdout.split()
        self.assertEqual(sorted(names), ["tests/BTest.php", "tests/[a]Test.php"], "the union over the slice's commits, not S2's")
        (tmp / "tests/[a]Test.php").write_text("2")
        self.assertEqual(git("diff", "--quiet", gate1, "--", ":(literal)tests/[a]Test.php", check=False).returncode, 1)
        self.assertEqual(git("diff", "--quiet", gate1, "--", "tests/NoSuchTest.php", check=False).returncode, 0,
                         "a path that exists nowhere passes silently: check each path exists in the gate commit")
        self.assertEqual(git("diff", "--quiet", "deadbeef", "--", "tests", check=False).returncode, 128)


class UntrackedFiles(unittest.TestCase):
    """Ruling 2."""

    def test_both_reviewers_list_untracked_files_with_uall(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertIn("git status --porcelain -uall", text)
                self.assertNotRegex(text, r"git status --porcelain(?! -uall)", "a bare porcelain status hides files inside untracked directories")

    def test_the_deep_reviewers_line_counts_include_untracked_files(self):
        self.assertRegex(body(self, "laravel-reviewer-deep"),
                         re.compile(r"untracked[^.]{0,240}(line count|changed lines|count)|(line count|changed lines|counts?)[^.]{0,240}untracked", I_S))


class DeepStaticChecks(unittest.TestCase):
    """Ruling 3."""

    def test_errors_in_unchanged_files_are_not_dropped_without_a_baseline(self):
        text = body(self, "laravel-reviewer-deep")
        self.assertRegex(text, re.compile(r"unchanged[^.]{0,300}reference[^.]{0,160}(changed )?(symbol|method|class)", I_S))
        self.assertIn("unverifiable: review by hand", text)
        self.assertRegex(text, re.compile(r"never[^.]{0,80}drop[^.]{0,240}(old|pre-?existing)[^.]{0,200}without a baseline", I_S))


class RefRangeMode(unittest.TestCase):
    """Ruling 4."""

    def test_a_named_pr_or_range_is_diffed_head_to_base_and_ignores_the_working_tree(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertRegex(text, re.compile(r"(PR|ref range)[^.]{0,400}git diff <base> <head>", I_S))
                self.assertRegex(text, re.compile(r"git diff <base> <head>[^.]{0,300}(ignore|ignoring)[^.]{0,80}working[- ]tree|(ignore|ignoring)[^.]{0,80}working[- ]tree[^.]{0,300}git diff <base> <head>", I_S))
                self.assertIn("gh pr view --json baseRefName", text)
                self.assertRegex(text, re.compile(r"never guess[^.]{0,120}(base|default branch)|(base|default branch)[^.]{0,200}never guess|ask[^.]{0,120}(base|default branch)", I_S))


class GateRerunScope(unittest.TestCase):
    """Ruling 5."""

    def test_only_a_filtered_pest_run_is_rerun(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertRegex(text, re.compile(r"only[^.]{0,120}`?(ddev exec )?vendor/bin/pest`?[^.]{0,200}--filter|vendor/bin/pest[^.]{0,80}with `?--filter`?[^.]{0,200}only", I_S))
                self.assertIn("claimed, not rerun (command not a filtered pest run)", text)

    def test_with_no_named_command_the_plan_or_ci_supplies_one(self):
        for stem in REVIEWERS:
            with self.subTest(agent=stem):
                self.assertRegex(body(self, stem), re.compile(r"(no (gate )?command (is )?named|names? no (gate )?command)[^.]{0,300}(plan|slice gate)[^.]{0,200}(CI|workflow)", I_S))

    def test_a_rerun_while_the_lock_check_failed_is_labelled(self):
        for stem in REVIEWERS:
            with self.subTest(agent=stem):
                self.assertRegex(body(self, stem), re.compile(r"lock check[^.]{0,120}(is |exit |-> )?1[^.]{0,300}weakened tests|weakened tests[^.]{0,300}lock check", I_S))


class G8ForReadOnlyReviewers(unittest.TestCase):
    """Ruling 6."""

    def test_reasons_from_the_test_or_raises_a_verify_with_the_revert_command(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            with self.subTest(agent=stem):
                self.assertRegex(text, re.compile(r"reason from the test and the changed lines|from the test and the changed lines", I_S))
                self.assertRegex(text, re.compile(r"Verify:[^.]{0,400}(exact )?(revert|git) command[^.]{0,200}(person|human|owner|caller)|Verify:[^.]{0,400}for (a|the) (person|human|owner|caller) to run", I_S))


class DeepReviewerTeam(unittest.TestCase):
    """Ruling 7."""

    def body(self):
        return body(self, "laravel-reviewer-deep")

    def test_every_lens_brief_gets_the_sensitive_paths_and_evidence_rules(self):
        self.assertRegex(self.body(), re.compile(r"(every|each) (lens )?(brief|prompt)[^.]{0,300}(paste|pasted|include|copy|copies)[^.]{0,300}Sensitive paths[^.]{0,200}Evidence", I_S))

    def test_deterministic_findings_cannot_be_refuted_by_the_challenger(self):
        text = self.body()
        self.assertRegex(text, re.compile(r"deterministic[^.]{0,300}(lock check)[^.]{0,200}(avoid)[^.]{0,200}(check-backed|backed by a (static )?check)", I_S))
        self.assertRegex(text, re.compile(r"deterministic[^.]{0,500}(cannot|can.t|never|not)[^.]{0,80}(refute|challeng)", I_S))

    def test_no_challenger_without_a_critical_or_important_finding(self):
        text = self.body()
        self.assertIn("Challenge: none (no Critical or Important findings)", text)
        self.assertRegex(text, re.compile(r"(zero|no|without any) Critical or Important[^.]{0,200}(no|not|never)[^.]{0,60}(challenger|challenge)", I_S))

    def test_agent_starts_are_limited_by_instruction_and_a_retry_counts(self):
        text = self.body()
        self.assertRegex(text, re.compile(r"agent starts?[^.]{0,80}limited by instruction[^.]{0,300}laravel-review-checker[^.]{0,200}\b5\b|limited by instruction[^.]{0,300}(checker type|laravel-review-checker)[^.]{0,300}at most 5", I_S))
        self.assertRegex(text, re.compile(r"retr(y|ies)[^.]{0,120}counts? against the cap", I_S))


class DebuggerRound2(unittest.TestCase):
    """Ruling 8."""

    def body(self):
        return body(self, "laravel-debugger")

    def test_bisect_needs_the_callers_go_and_a_restore(self):
        text = self.body()
        self.assertRegex(text, re.compile(r"git bisect[^.]{0,300}caller.s go[^.]{0,300}restore[^.]{0,120}(original|starting) ref", I_S))
        for cmd in ("git log -p", "git blame", "git show"):
            self.assertIn(cmd, text)
        self.assertRegex(text, re.compile(r"(otherwise|without (the caller.s )?go)[^.]{0,200}git log -p", I_S))

    def test_the_regression_test_goes_in_a_new_file_never_a_gate_file(self):
        self.assertRegex(self.body(), re.compile(r"regression test[^.]{0,200}new file[^.]{0,200}never[^.]{0,80}gate file", I_S))

    def test_a_cycle_with_no_surviving_hypothesis_is_a_round(self):
        self.assertRegex(self.body(), re.compile(r"(hypothesis cycle|cycle)[^.]{0,240}no (surviving )?hypothesis[^.]{0,160}counts as a round", I_S))

    def test_migrate_and_dev_database_writes_need_the_callers_go(self):
        self.assertRegex(self.body(), re.compile(r"`?migrate`?[^.]{0,300}(any write|write)[^.]{0,120}dev(elopment)? database[^.]{0,200}caller.s go", I_S))


class Nits(unittest.TestCase):
    """Ruling 9."""

    def test_the_budget_exemption_is_the_exact_name(self):
        proc = s9.run_budget(s8.FIX / "agent-other-reviewer-deep")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("must disallow Agent", proc.stdout)
        ok = s9.run_budget(s8.FIX / "agent-reviewer-deep-orchestrator")
        self.assertEqual(ok.returncode, 0, ok.stdout)

    def test_reviewer_bash_forbid_lists_are_complete(self):
        for stem in REVIEWERS:
            text = body(self, stem)
            for needle in ("git restore", "git clean", "git apply", "git rebase", "git merge", "git pull", "git diff --output="):
                with self.subTest(agent=stem, forbidden=needle):
                    self.assertIn(needle, text)

    def test_mode_lines_carry_the_static_check_summary_and_the_left_out_counts(self):
        text = body(self, "laravel-reviewer-deep")
        self.assertRegex(text, r"Mode: single pass \(<reason>\)[^\n]{0,80}static checks:")
        self.assertRegex(text, r"static checks:[^\n]*left out")


class TestModuleImport(unittest.TestCase):
    def test_the_module_imports_from_the_repo_root(self):
        proc = subprocess.run([sys.executable, "-m", "unittest", "tests.gate.test_s9.AgentFiles.test_names_no_outside_model_or_builder"],
                              capture_output=True, text=True, cwd=s8.REPO, env={k: v for k, v in os.environ.items()})
        self.assertNotIn("ModuleNotFoundError", proc.stderr, proc.stderr)


if __name__ == "__main__":
    unittest.main()
