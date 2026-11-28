"""The gated-build skill: the main session runs a gated slice through the outside builders the profile names.

Requirements R18, R26, R27; acceptance criteria AC26 (gate commit first, the outside builder gets the brief
file, the lock check and the checker run on its result), AC27 (a hand-back missing a line is reported and not
a pass), AC28 (an outside builder that exits with an error: the build continues with the next builder named,
or the package's own builder, and says so in the report).
Contract: tests/OutsideBuilders/CONTRACT.md, section "Skill". As in the earlier agent gates, a rule counts
only when one line (paragraph or bullet) of the skill carries it by its operative words. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_gated_build_skill.py'
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import (  # noqa: E402
    CALL_FORM, LOCK_COMMITTED, LOCK_TREE, NAMED_MODELS, REPO, SKILL, assert_line, read_new,
)


def gated_build_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip("'\"")
    return out


class SkillFile(unittest.TestCase):
    """R18: the procedure ships as a Boost skill."""

    def test_the_skill_exists_with_its_name_and_a_description(self):
        text = read_new(self, SKILL)
        meta = gated_build_frontmatter(text)
        self.assertEqual(meta.get("name"), "laravel-gated-build")
        self.assertTrue(meta.get("description"), "the skill has no description")

    def test_the_skill_passes_the_skill_validator(self):
        read_new(self, SKILL)
        proc = subprocess.run(["bash", "scripts/validate-skills.sh"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_skill_names_no_model_or_team_tool(self):
        text = read_new(self, SKILL)
        for term in NAMED_MODELS:
            self.assertIsNone(re.search(rf"(?i)(?<![a-z-]){re.escape(term)}(?![a-z-])", text), f"the skill names {term}")


class GateCommitFirst(unittest.TestCase):
    """AC26, R18: the same gate writer runs first, before any builder."""

    def test_the_gate_writer_commits_the_gate_before_any_builder_runs(self):
        text = read_new(self, SKILL)
        assert_line(self, text, r"`?laravel-gate-writer`?", r"(first|before)", r"builder",
                    label="laravel-gate-writer runs first and commits the gate before any builder")
        self.assertIn("test(gate): <slice id>", text)

    def test_builders_come_from_the_profile_in_order(self):
        assert_line(self, read_new(self, SKILL), r"skills-profile\.json", r"`?builders`?", r"order",
                    label="the outside builders are the profile's builders, tried in order")


class BriefFile(unittest.TestCase):
    """AC26, R26: the outside builder gets the brief file, in the documented format."""

    def test_each_builder_is_called_with_the_brief_file(self):
        text = read_new(self, SKILL)
        self.assertIn(CALL_FORM, text)
        assert_line(self, text, r"brief", r"docs/brief-format\.md|brief-format",
                    label="the brief is written in the format of docs/brief-format.md")


class ChecksOnTheResult(unittest.TestCase):
    """AC26, AC27, R18, R26: lock checks, the hand-back check and the checker run on the outside builder's result."""

    def test_both_lock_checks_run_on_the_result(self):
        text = read_new(self, SKILL)
        self.assertIn(LOCK_COMMITTED, text)
        self.assertIn(LOCK_TREE, text)

    def test_a_hand_back_missing_a_line_is_reported_and_not_a_pass(self):
        assert_line(self, read_new(self, SKILL), r"handback_check\.py", r"missing",
                    r"(not (count as )?a pass|never (counts as )?a pass|not counted as a pass)",
                    label="a hand-back the checker rejects is reported with its missing line and not counted as a pass")

    def test_the_hand_back_is_checked_before_the_checker_runs(self):
        assert_line(self, read_new(self, SKILL), r"handback_check",
                    r"before (the |any |starting )?(`?laravel-review-checker`?|checker)|(`?laravel-review-checker`?|checker)[^.]{0,80}after",
                    label="the hand-back check runs before the checker")

    def test_the_checker_runs_on_the_outside_result(self):
        assert_line(self, read_new(self, SKILL), r"`?laravel-review-checker`?", r"outside",
                    label="laravel-review-checker runs on the outside builder's result, as for the package's own builder")

    def test_three_rounds_per_builder(self):
        assert_line(self, read_new(self, SKILL), r"\b3 rounds\b", r"builder",
                    label="at most 3 rounds per builder, then the next builder")


class Fallback(unittest.TestCase):
    """AC28, R27: a failed, timed-out or unavailable builder hands over to the next, and the build says so."""

    def test_an_unavailable_builder_hands_over_to_the_next(self):
        assert_line(self, read_new(self, SKILL), r"exit 3", r"next builder",
                    label="exit 3 (unavailable): next builder")

    def test_a_builder_that_exits_with_an_error_hands_over_to_the_next(self):
        assert_line(self, read_new(self, SKILL), r"(any other|other|nonzero|non-zero) exit", r"next builder",
                    label="any other exit (failed): next builder")

    def test_a_builder_that_times_out_hands_over_to_the_next(self):
        assert_line(self, read_new(self, SKILL), r"`?timeout_minutes`?", r"(next builder|failed)",
                    label="no exit within timeout_minutes counts as failed: next builder")

    def test_the_tree_is_reset_before_each_builder(self):
        text = read_new(self, SKILL)
        self.assertIn("git reset --hard", text)
        self.assertIn("git clean -fd", text)
        assert_line(self, text, r"before (each|every|the next) builder", label="the slice is reset before each builder")

    def test_a_failed_builders_commits_and_files_are_removed_before_the_next(self):
        assert_line(self, read_new(self, SKILL), r"git reset --hard", r"(<base>|base|gate commit)",
                    label="git reset --hard back to the base (the gate commit), so a failed builder's commits go")
        assert_line(self, read_new(self, SKILL), r"git clean -fd", label="git clean -fd removes a failed builder's untracked files")

    def test_the_package_builder_is_the_last_fallback(self):
        assert_line(self, read_new(self, SKILL), r"`?laravel-builder`?", r"same brief",
                    label="when every outside builder fails, laravel-builder builds the slice from the same brief")

    def test_the_report_names_each_builder_tried_and_never_stops_silently(self):
        text = read_new(self, SKILL)
        assert_line(self, text, r"report", r"(each|every) builder", r"(exit|outcome|result)",
                    label="the report names each builder tried with its exit or outcome")
        assert_line(self, text, r"never (stop|stops|ends?) silently", label="the gated build never stops silently")
        self.assertIn("Builder: <name>", text)


if __name__ == "__main__":
    unittest.main()
