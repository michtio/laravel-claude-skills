"""Gate test for slice S9d-1 (laravel-layer): process rules in the agents.

Requirements R15, R17. Decisions log 2026-11-27 (consolidation before every release: the builder gets a
consolidation mode, brief and hand-back lines). Skills-gaps row 136.
Contract: tests/S9d1/CONTRACT.md section 18. Standard library only; no DDEV, no network.

As in S9b and S9c, a rule counts only when ONE paragraph or bullet (one line) of the agent's own file
carries it, by its operative words; hand-back lines are read from the fenced template.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from test_s9b_agents import fenced_blocks, one_line  # noqa: E402


def builder() -> str:
    return s8.agent_path("laravel-builder").read_text(encoding="utf-8")


def gate_writer() -> str:
    return s8.agent_path("laravel-gate-writer").read_text(encoding="utf-8")


class ConsolidationMode(unittest.TestCase):
    def test_consolidation_mode_changes_no_behavior_and_no_test(self):
        line = one_line(self, builder(), r"consolidation", r"(no|never|without)\b[^.]{0,40}behavio", r"tests/",
                        label="consolidation mode: no behavior change, nothing under tests/ changes")
        self.assertRegex(line, r"git diff --quiet <base> HEAD -- tests/", "the gate is the tests unchanged against the base commit")

    def test_consolidation_brief_shape(self):
        line = one_line(self, builder(), r"consolidation", r"brief", r"\bbase\b",
                        label="a consolidation brief names the base commit and the scope it may touch")
        self.assertRegex(line, r"(?i)(scope|paths?|areas?)")
        self.assertRegex(line, r"(?i)(duplicat|dead code|split)")

    def test_consolidation_hand_back_lines(self):
        blocks = [b for b in fenced_blocks(builder()) if "Built:" in b]
        self.assertTrue(blocks, "the builder's hand-back template is missing")
        for name in ("Duplicates merged:", "Dead code removed:", "Files split:", "Tests unchanged:"):
            self.assertRegex(blocks[0], rf"(?m)^{re.escape(name)}", f"hand-back line {name} is missing")


class BuilderWorkflowsAfterASetupChange(unittest.TestCase):
    # Row 140, builder half: the setup's own workflow got the database service, the project's other one did not
    def test_every_ci_workflow_reaches_the_pinned_database_before_the_first_push(self):
        line = one_line(self, builder(), r"(every|each|all)[^.]{0,40}(CI )?workflows?", r"database", r"(push|before)",
                        label="after a setup change that pins a real test database, every CI workflow that runs the tests can reach it before the first push")
        self.assertRegex(line, r"(?i)(setup|test_database|pin)")


class GateWriterUniformRed(unittest.TestCase):
    # Row 136: one shared fixture fails first for every test
    def test_a_shared_fixture_that_fails_first_is_handled(self):
        line = one_line(self, gate_writer(), r"(shared|one) (fixture|helper|boot)", r"(uniform|same (first )?(red|reason)|every test)",
                        label="when a shared fixture fails first, every test shares one red reason")
        self.assertRegex(line, r"(?i)(next layer|stub)")
        self.assertRegex(line, r"(?i)revert")
        self.assertRegex(line, r"(?i)(hand-back|Passability)")


if __name__ == "__main__":
    unittest.main()
