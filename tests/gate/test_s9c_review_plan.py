"""Gate test for slice S9c (laravel-layer): reviewer, deep reviewer, checker and planner rules from the field test.

Requirements R15, R16, R17, R25. Skills-gaps rows 96 to 100, 118, the reviewer side of 97 for the
checker and the deep reviewer (the same evidence rule), and the open part of row 17 (the planner fixes
public names). Contract: tests/S9c/CONTRACT.md section 4. Standard library only; no DDEV, no network.

Each test checks that the agent file carries a rule in ONE paragraph or bullet (one line), by the
operative words, not by a fixed sentence.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from test_s9b_agents import fenced_blocks, one_line, section  # noqa: E402


def text(stem: str) -> str:
    return s8.agent_path(stem).read_text(encoding="utf-8")


QUOTED_PIPE_FILTER = r"ddev exec \"vendor/bin/pest --filter='[^'\"]*\|"


def assert_pest_exit_rule(test: unittest.TestCase, stem: str) -> None:
    """Round 2 amendment (F1). PHPUnit exits 2 when a run has errors (ShellExitCodeCalculator::EXCEPTION_EXIT,
    vendor/phpunit/phpunit/src/TextUI/ShellExitCodeCalculator.php, PHPUnit 13.4.7), so exit 2 with a result line
    is a fail, not a broken run. Exit 0 pass; exit 1, or exit 2 with a `Tests:` line, fail; no result line or any
    other exit, broken."""
    body = s8.agent_path(stem).read_text(encoding="utf-8")
    line = one_line(test, body, r"exit 2", r"Tests:", r"broken",
                    label=f"{stem}: pest exit 0 is pass; exit 1, or exit 2 with a Tests: result line, is a fail; no result line or any other exit is broken")
    test.assertRegex(line, r"(?i)exit 0[^.;]{0,40}pass")
    test.assertRegex(line, r"(?i)exit 1[^.;]{0,80}fail|fail[^.;]{0,80}exit 1")
    test.assertRegex(line, r"(?i)(no|without a|missing)[^.;]{0,20}(`?Tests:`? )?result line")
    test.assertRegex(line, r"(?i)(any other exit|other exits?)")
    for l in body.splitlines():
        test.assertNotRegex(l, r"(?i)(pest|phpunit|rerun|red run)[^.\n]{0,120}(other than 0 or 1|neither 0 nor 1)",
                            f"{stem}: a pest exit other than 0 or 1 is not broken: exit 2 with a result line is a fail")


class Reviewer(unittest.TestCase):
    STEM = "laravel-reviewer"

    # Row 96
    def test_a_rerun_with_a_pipe_in_the_filter_quotes_the_whole_container_command(self):
        self.assertRegex(text(self.STEM), QUOTED_PIPE_FILTER)

    def test_a_rerun_reads_the_pest_exit_with_its_result_line(self):
        # Amended in round 2 (F1): was "a pest exit other than 0 or 1 is a broken rerun".
        assert_pest_exit_rule(self, self.STEM)

    # Row 97
    def test_any_installed_vendor_package_is_evidence_for_its_own_behavior(self):
        line = one_line(self, text(self.STEM), r"vendor/", r"(any|every) (installed )?(vendor )?package", r"evidence",
                        label="any installed package's source under vendor/ is evidence for that package's behavior")
        self.assertRegex(line, r"(?i)(file:line|path and line|cited)")

    def test_a_driver_dependent_defect_may_be_important_with_its_reproduction(self):
        line = one_line(self, text(self.STEM), r"driver", r"Important", r"(not run|was not run|could not run)",
                        label="a driver-dependent defect (column type and the query read) may be Important when the report says it was not run and gives the reproduction")
        self.assertRegex(line, r"(?i)column")
        self.assertRegex(line, r"(?i)reproduc")

    # Row 98
    def test_the_report_has_a_merge_line(self):
        blocks = [b for b in fenced_blocks(text(self.STEM)) if "Lock check:" in b and "### Critical" in b]
        self.assertTrue(blocks, "the reviewer's report template is missing")
        self.assertRegex(blocks[0], r"(?m)^Merge: blocked by [^\n]*\| not blocked")

    def test_the_r_table_can_be_met_on_one_driver_and_not_another(self):
        one_line(self, section(text(self.STEM), "Report"), r"met on <driver>", r"not met on <driver>",
                 label="the R table can carry `met on <driver>, not met on <driver>`")

    # Row 99
    def test_a_missing_preloaded_skill_is_read_from_its_installed_folder(self):
        line = one_line(self, text(self.STEM), r"preload", r"(missing|absent|not preloaded|not loaded)", r"\.claude/skills",
                        label="a preloaded skill that did not load is read from .claude/skills/<name> and its absence named in the report")
        self.assertRegex(line, r"(?i)report")

    def test_a_package_without_a_register_row_is_reported_as_no_verdict(self):
        one_line(self, text(self.STEM), r"(package (with no|without a) (register )?row|no row in the register)", r"`no verdict`",
                 label="a package without a register row is reported as `no verdict`")

    # Row 100
    def test_security_checks_cover_auth_flows(self):
        line = one_line(self, section(text(self.STEM), "Checks"), r"auth flows", r"(nonce|challenge)", r"replay",
                        label="an Auth flows item: challenge freshness and single use, replay, session stamps, remember-me, fixation, events carrying the full user")
        for pattern in (r"remember", r"fixation", r"(full user|user model)", r"(stamp|session)"):
            self.assertRegex(line, rf"(?i){pattern}")
        self.assertRegex(line, r"(?i)(docs|documentation)", "check what the code enforces against what the docs hand to the consumer")


class ReviewerDeep(unittest.TestCase):
    STEM = "laravel-reviewer-deep"

    # Row 118 (a): the checker type is not in the agent list
    def test_a_missing_checker_type_gets_general_purpose_stand_ins(self):
        line = one_line(self, text(self.STEM), r"general-purpose", r"laravel-review-checker\.md",
                        label="checker type not in the agent list: general-purpose stand-ins with the checker file as instructions, named in the Mode line")
        self.assertRegex(line, r"(?i)(not in (your|the) agent list|missing|not installed)")
        self.assertRegex(line, r"(?i)Mode")

    # Row 118 (b), with row 97
    def test_any_installed_vendor_package_is_evidence(self):
        line = one_line(self, text(self.STEM), r"vendor/", r"(any|every) (installed )?(vendor )?package", r"evidence",
                        label="any installed package's source under vendor/ is evidence for that package's behavior")
        self.assertRegex(line, r"(?i)(file:line|path and line|cited)")

    # Row 118 (c)
    def test_a_store_used_as_a_security_control_is_a_sensitive_path(self):
        line = one_line(self, text(self.STEM), r"(cache|session|lock)[^.]{0,30}store", r"(single use|rate limit|replay)", r"every driver",
                        label="a cache, session or lock store used for single use, rate limits or replay: read add, put, get and expiry for every driver the config can name")
        self.assertRegex(line, r"\badd\b")
        self.assertRegex(line, r"(?i)expir")

    # Row 96 (same rerun rule)
    def test_a_rerun_with_a_pipe_in_the_filter_quotes_the_whole_container_command(self):
        self.assertRegex(text(self.STEM), QUOTED_PIPE_FILTER)

    def test_a_rerun_reads_the_pest_exit_with_its_result_line(self):
        # Amended in round 2 (F1): was "a pest exit other than 0 or 1 is a broken rerun".
        assert_pest_exit_rule(self, self.STEM)


class Checker(unittest.TestCase):
    STEM = "laravel-review-checker"

    # Row 97 (same evidence rule)
    def test_any_installed_vendor_package_is_evidence(self):
        one_line(self, text(self.STEM), r"vendor/", r"(any|every) (installed )?(vendor )?package", r"evidence",
                 label="any installed package's source under vendor/ is evidence for that package's behavior")


class Planner(unittest.TestCase):
    STEM = "laravel-planner"

    def template(self) -> str:
        blocks = [b for b in fenced_blocks(text(self.STEM)) if "**Deliverable:**" in b]
        if not blocks:
            self.fail("the planner's slice template is missing")
        return blocks[0]

    # Row 17 (open part)
    def test_every_slice_fixes_the_public_names_its_criteria_rely_on(self):
        line = one_line(self, text(self.STEM), r"public names", r"gate writer",
                        label="the planner fixes the public names (classes, methods, config keys, env vars, constants, event names) in the slice before the gate writer starts")
        for kind in (r"class", r"method", r"config key", r"env"):
            self.assertRegex(line, rf"(?i){kind}")

    def test_the_slice_template_has_a_public_names_line(self):
        self.assertRegex(self.template(), r"(?m)^- \*\*Public names:\*\*")


if __name__ == "__main__":
    unittest.main()
