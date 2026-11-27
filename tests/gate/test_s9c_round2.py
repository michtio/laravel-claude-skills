"""Gate test for slice S9c (laravel-layer), round 2: the PR #12 review findings F1 to F13.

Requirements R7 (as amended 2026-11-27), R15, R17. Contract: tests/S9c/CONTRACT.md section 9.
Standard library only; no DDEV, no network.

Each rule is checked in ONE paragraph or bullet (one line) of the agent file it belongs to, by the
operative words, as in round 1. Round 1 tests that pinned a wrong rule are amended in place (listed in
the contract); this file adds the rules round 1 did not pin.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from test_s9b_agents import fenced_blocks, one_line, section  # noqa: E402
from test_s9c_review_plan import assert_pest_exit_rule  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
REVIEWERS = ("laravel-reviewer", "laravel-reviewer-deep")
# Where the pack's agent file is when the pack is a Claude Code plugin: ${CLAUDE_PLUGIN_ROOT} resolves in agent
# Markdown bodies to the installed version directory, ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/
# (https://code.claude.com/docs/en/plugins-reference, "Environment variables";
# https://code.claude.com/docs/en/plugins/loading.md, "Find plugins on disk").
PLUGIN_PATH = r"(\$\{CLAUDE_PLUGIN_ROOT\}/agents/|\.claude/plugins/cache/)"
DEFERRAL = r"(later|out of scope|follow-up|follow up|defer)"


def text(stem: str) -> str:
    return s8.agent_path(stem).read_text(encoding="utf-8")


def block_with(test: unittest.TestCase, stem: str, *markers: str) -> str:
    for b in fenced_blocks(text(stem)):
        if all(m in b for m in markers):
            return b
    test.fail(f"{stem}: no fenced template holding {markers}")


class F1PestExit(unittest.TestCase):
    """Exit 0 pass; exit 1, or exit 2 with a `Tests:` line, fail; no result line or any other exit, broken."""

    def test_builder(self):
        assert_pest_exit_rule(self, "laravel-builder")

    def test_reviewer(self):
        assert_pest_exit_rule(self, "laravel-reviewer")

    def test_deep_reviewer(self):
        assert_pest_exit_rule(self, "laravel-reviewer-deep")


class F2F7StandIns(unittest.TestCase):
    def test_builder_checker_stand_in_carries_the_checkers_restriction_and_plugin_path(self):
        line = one_line(self, section(text("laravel-builder"), "Checker gate"), r"general-purpose", r"laravel-review-checker\.md",
                        label="the checker stand-in's prompt carries the checker's restriction")
        self.assert_checker_restriction(line)
        self.assertRegex(line, PLUGIN_PATH)

    def test_deep_reviewer_checker_stand_in_carries_the_restriction_and_plugin_path(self):
        line = one_line(self, text("laravel-reviewer-deep"), r"general-purpose", r"laravel-review-checker\.md",
                        label="the checker stand-ins' prompts carry the checker's restriction")
        self.assert_checker_restriction(line)
        self.assertRegex(line, PLUGIN_PATH)

    def assert_checker_restriction(self, line: str) -> None:
        self.assertRegex(line, r"(?i)prompt")
        self.assertRegex(line, r"(?i)never[^.]{0,200}(write|edit)")
        self.assertRegex(line, r"(?i)tinker")
        self.assertRegex(line, r"(?i)record-rule")
        self.assertRegex(line, r"(?i)(start|starts|starting) (no |any )?agents?|agents?[^.]{0,20}start")

    def test_builder_gate_writer_stand_in_carries_the_restriction_and_plugin_path(self):
        line = one_line(self, text("laravel-builder"), r"general-purpose", r"laravel-gate-writer\.md",
                        label="the gate writer stand-in's prompt: writes only under tests/, never starts agents")
        self.assertRegex(line, r"(?i)prompt")
        self.assertRegex(line, r"only under `?tests/")
        self.assertRegex(line, r"(?i)never[^.]{0,80}(start|starts) (any )?agents?|(starts|start) no agents?")
        self.assertRegex(line, PLUGIN_PATH)

    def test_the_frontmatter_model_is_the_one_exception_to_pass_no_model(self):
        for stem in ("laravel-builder", "laravel-reviewer-deep"):
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"pass no `?model`?", r"(exception|except)", r"general-purpose",
                                label=f"{stem}: a general-purpose stand-in passes the agent file's frontmatter model, the one exception to 'pass no model'")
                self.assertRegex(line, r"(?i)frontmatter model")
                self.assertRegex(line, r"(?i)\b(one|only)\b[^.]{0,20}exception")


# F3 (the commit recipe) is pinned by the amended round 1 test
# test_s9c_builder.GitAndLockCheck.test_the_commit_recipe_stages_nothing_until_commit_time.


class F4SupersededInReviews(unittest.TestCase):
    def test_both_reviewers_use_the_no_own_files_line_never_an_empty_pathspec(self):
        for stem in REVIEWERS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"supersed", r"no own files \(superseded by",
                                label=f"{stem}: a superseded gate commit gets `no own files (superseded by <hash>)`")
                self.assertRegex(line, r"(?i)(empty pathspec|never[^.]{0,60}lock-check|not lock-checked)")


class F5ProjectFilesAndR7(unittest.TestCase):
    CHECKERS = ("laravel-reviewer", "laravel-reviewer-deep", "laravel-review-checker")

    def test_reviewers_and_checker_check_project_files(self):
        for stem in self.CHECKERS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"README", r"CHANGELOG", r"(changes behavior|behavior a user|user-facing)",
                                label=f"{stem}: a diff that changes behavior without updating the README, docs and CHANGELOG is a finding")
                self.assertRegex(line, r"(?i)Important")

    def test_reviewers_and_checker_check_r7(self):
        for stem in self.CHECKERS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"README", r"(never cites?|cites?) tests?", r"(docblock|comment)",
                                label=f"{stem}: R7, a README never cites tests; a docblock or comment that claims behavior names its test")
                self.assertRegex(line, r"(?i)names? (the|its) test")

    def test_debugger_hand_back_has_a_project_files_line(self):
        self.assertRegex(block_with(self, "laravel-debugger", "Root cause:"), r"(?m)^Project files: ")

    def test_gate_writer_carries_the_found_defect_rule(self):
        line = one_line(self, text("laravel-gate-writer"), r"defect", rf"(never|not)\b[^.]{{0,80}}{DEFERRAL}",
                        label="the gate writer: a found defect is fixed or raised, never deferred")
        self.assertRegex(line, r"(?i)(owner|Open|raise)")


class F6Merge(unittest.TestCase):
    def test_merge_is_the_defined_last_result_line_in_both_reviewers(self):
        for stem in REVIEWERS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"Merge:", r"(last|final) result line",
                                label=f"{stem}: `Merge:` is the last result line: blocked on any Critical or Important finding or an unmet MUST")
                self.assertRegex(line, r"(?i)blocked")
                self.assertRegex(line, r"Critical")
                self.assertRegex(line, r"Important")
                self.assertRegex(line, r"MUST")
                self.assertRegex(line, r"(?i)not blocked")

    def test_changelog_states_the_merge_rule(self):
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = section(changelog, "[Unreleased]")
        line = one_line(self, unreleased, r"Merge:", r"(Critical|Important)",
                        label="CHANGELOG: the Merge: line reads blocked on a Critical or Important finding or an unmet MUST")
        self.assertRegex(line, r"MUST")
        self.assertNotRegex(unreleased, r"end with a `Merge:` line", "the old wording said the reviewers end with Merge:, but Learnings is last")


class F8FoundDefectCriterion(unittest.TestCase):
    def assert_criterion(self, line: str) -> None:
        self.assertRegex(line, r"(?i)\bunless\b")
        self.assertRegex(line, r"(?i)ruling")
        self.assertRegex(line, r"(?i)spec")
        self.assertRegex(line, r"(?i)public API")
        self.assertRegex(line, r"(?i)scope")

    def test_builder(self):
        line = one_line(self, text("laravel-builder"), r"defect", r"\bfix", r"unless",
                        label="builder: fix a found defect unless the fix needs a ruling; then stop at a passing gate and raise it under Open")
        self.assert_criterion(line)
        self.assertRegex(line, r"(?i)passing gate")
        self.assertRegex(line, r"Open")

    def test_builder_step_4_no_longer_reports_a_predating_failure_unfixed(self):
        self.assertNotRegex(text("laravel-builder"), r"(?i)reported, not (silently )?fixed")

    def test_debugger_and_planner(self):
        for stem in ("laravel-debugger", "laravel-planner"):
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"defect", r"\bfix", r"unless",
                                label=f"{stem}: fix a found defect unless the fix needs a ruling (spec, public API, scope)")
                self.assert_criterion(line)

    def test_readme(self):
        readme = section((REPO / "README.md").read_text(encoding="utf-8"), "Agents")
        line = one_line(self, readme, r"defect", r"\bfix", r"unless",
                        label="README Agents: fix a found defect unless the fix needs a ruling")
        self.assert_criterion(line)


class F9Workflow(unittest.TestCase):
    def test_a_workflow_adding_slice_validates_locally_or_on_the_pr_else_open_not_run(self):
        line = one_line(self, text("laravel-builder"), r"workflow", r"actionlint", r"not run",
                        label="a workflow-adding slice runs actionlint locally or the pushed PR's checks; without a push, Open says not run")
        self.assertRegex(line, r"(?i)local")
        self.assertRegex(line, r"(?i)(pushed )?(PR|pull request)")
        self.assertRegex(line, r"Open")


class F10BuilderHandBack(unittest.TestCase):
    def block(self) -> str:
        return block_with(self, "laravel-builder", "Gate flow:", "Built:")

    def test_tests_line_with_the_proof_forms(self):
        line = next((l for l in self.block().splitlines() if l.startswith("Tests:")), "")
        self.assertTrue(line, "the hand-back has a Tests: line")
        self.assertRegex(line, r"red \(<reason>\) -> green")
        self.assertRegex(line, r"green \(pin\) -> red under")
        self.assertRegex(line, r"migrated")

    def test_found_defects_line(self):
        self.assertRegex(self.block(), r"(?m)^Found defects: ")

    def test_revert_to_prove_is_one_line_per_fix(self):
        line = next((l for l in self.block().splitlines() if l.startswith("Revert-to-prove:")), "")
        self.assertRegex(line, r"(?i)(one (line )?per fix|per fix)")


class F11GateWriterQuestion(unittest.TestCase):
    def test_builder_answers_a_gate_writer_question_and_rebriefs(self):
        line = one_line(self, text("laravel-builder"), r"gate writer", r"question", r"(re-?brief|brief it again)",
                        label="when the gate writer returns a question instead of a commit: answer from the spec verbatim, or ask the owner, then re-brief")
        self.assertRegex(line, r"(?i)(instead of|no|without) (a )?(gate )?commit")
        self.assertRegex(line, r"(?i)verbatim")
        self.assertRegex(line, r"(?i)owner")

    def test_gate_writer_rules_name_the_temporary_install_exception(self):
        line = one_line(self, section(text("laravel-gate-writer"), "Rules"), r"only under `?tests/", r"composer\.json",
                        label="the Rules' write-only-under-tests bullet names the temporary-install exception for composer.json")
        self.assertRegex(line, r"(?i)temporar")
        self.assertRegex(line, r"(?i)(restore|revert)")


class F12OpenAndAttribution(unittest.TestCase):
    def test_gate_writer_amendment_stat_goes_under_open(self):
        line = one_line(self, text("laravel-gate-writer"), r"amend", r"git diff --stat",
                        label="the amendment's git diff --stat goes under Open")
        self.assertRegex(line, r"\bOpen\b")

    def test_gate_writer_superseded_rulings_go_under_open(self):
        line = one_line(self, text("laravel-gate-writer"), r"supersed", r"final",
                        label="superseded rulings are named under Open")
        self.assertRegex(line, r"\bOpen\b")

    def test_gate_writer_count_note_goes_under_open(self):
        line = one_line(self, text("laravel-gate-writer"), r"\bcount", r"source",
                        label="how a count was read goes under Open")
        self.assertRegex(line, r"\bOpen\b")

    # The builder's absolute attribution rule is pinned by the amended round 1 test
    # test_s9c_builder.Environment.test_commits_and_pr_bodies_never_carry_a_trailer_or_attribution.


class F13ReportEndings(unittest.TestCase):
    def test_checker_empty_reply_is_no_findings_plus_learnings(self):
        line = one_line(self, text("laravel-review-checker"), r"No findings for", r"Learnings",
                        label="the checker's empty reply is `No findings for <lens>.` and the Learnings line")

    def test_learnings_is_last_in_both_reviewers(self):
        for stem in REVIEWERS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"Learnings", r"\blast\b",
                                label=f"{stem}: the report order puts Learnings last, after Merge")
                self.assertRegex(line, r"Merge")

    def test_reviewer_template_ends_with_merge_then_learnings(self):
        block = block_with(self, "laravel-reviewer", "Lock check:", "### Critical")
        rows = [l for l in block.splitlines() if l.strip()]
        self.assertTrue(rows[-1].startswith("Learnings:"), f"the template's last line is {rows[-1]!r}")
        self.assertTrue(rows[-2].startswith("Merge:"), f"the line before Learnings is {rows[-2]!r}")


if __name__ == "__main__":
    unittest.main()
