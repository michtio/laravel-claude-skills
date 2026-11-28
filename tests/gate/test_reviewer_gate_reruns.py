"""Reviewers rerun gates written the new way: a pest run narrowed by --filter, --group or a test file path.

Requirements R17 (G5: reviewers rerun the gates). The planner, builder and gate writer now write gates as
`--group=<id>` or a file path (decisions log 2026-11-27, "Human-readable tests"); a reviewer that reruns
only `--filter` runs reports every such gate "claimed, not rerun", so G5 never runs it.
Contract: tests/SkillContent/CONTRACT.md, section "Reviewer gate reruns".

Each reviewer's own file carries, in one paragraph or bullet:
- the allowance: `vendor/bin/pest` narrowed by `--filter`, `--group` or a test file path, never an
  unfiltered run;
- the fallback when no gate command is named (the plan's gate, else CI's test step), which applies the same
  narrowing forms, so a plan gate written as `--group=` or a file path is rerun.
The old filter-only allowance is gone. The not-rerun reason string `(command not a filtered pest run)` stays: the
locked S9 round 2 gate pins it exactly, and it reads as "not narrowed".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import agent, line_in  # noqa: E402

ALLOWANCE = (r"vendor/bin/pest", r"--filter", r"--group", r"(test file|file path)", r"unfiltered")
FALLBACK = (r"no gate command named", r"--group", r"(test file|file path)")
OLD_ALLOWANCE = "`ddev exec vendor/bin/pest` with `--filter`"


class Reviewer(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-reviewer")

    def test_a_pest_run_narrowed_by_filter_group_or_file_is_rerun(self):
        line_in(self, self.text(), *ALLOWANCE,
                label="rerun vendor/bin/pest narrowed by --filter, --group or a test file path, never an unfiltered run")
        self.assertNotIn(OLD_ALLOWANCE, self.text(), "the reviewer still reruns only a pest run with --filter")

    def test_the_gates_fallback_applies_the_same_narrowing_forms(self):
        line_in(self, self.text(), *FALLBACK,
                label="Gates fallback (plan gate, else CI test step) reruns a gate narrowed by --group or a test file path too")


class DeepReviewer(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-reviewer-deep")

    def test_a_pest_run_narrowed_by_filter_group_or_file_is_rerun(self):
        line_in(self, self.text(), *ALLOWANCE,
                label="rerun vendor/bin/pest narrowed by --filter, --group or a test file path, never an unfiltered run")
        self.assertNotIn(OLD_ALLOWANCE, self.text(), "the deep reviewer still reruns only a pest run with --filter")

    def test_the_gates_fallback_applies_the_same_narrowing_forms(self):
        line_in(self, self.text(), *FALLBACK,
                label="Gates fallback (plan gate, else CI test step) reruns a gate narrowed by --group or a test file path too")


if __name__ == "__main__":
    unittest.main()
