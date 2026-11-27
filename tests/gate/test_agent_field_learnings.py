"""Agent rules from the field test: concurrency gates, mutation proofs, existing tests, dev services,
helper scope, and the deep reviewer's evidence and report.

Requirements R15, R16, R17. Gaps rows 130, 141, 152, 160, 164 and 168 (gate writer), 142 and 161
(builder), 164 (planner), 146, 147 and 152 (deep reviewer).
Contract: tests/SkillContent/CONTRACT.md, section "Agent rules".

As in the earlier agent gates, a rule counts only when one paragraph or bullet of the agent's own file
carries it by its operative words.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import agent, line_in  # noqa: E402


class GateWriterConcurrency(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-gate-writer")

    def test_a_parallel_criterion_points_to_the_racer_pattern(self):
        # Row 130, agent half
        line_in(self, self.text(), r"(parallel|concurrent)", r"racer",
                label="when a criterion says parallel or concurrent, use the racer pattern of the testing notes")

    def test_a_single_use_gate_interleaves_between_read_and_update(self):
        # Row 141, agent half
        line_in(self, self.text(), r"single-use", r"interleav", r"(read|SELECT)", r"update",
                label="a single-use gate interleaves a second consume between the read and the update")

    def test_a_concurrency_gate_races_every_write_path(self):
        # Row 152, gate writer half
        line_in(self, self.text(), r"concurrency gate", r"every write path",
                label="a concurrency gate races every write path of the slice, with a transaction or not")
        line_in(self, self.text(), r"(same cost|constant time)", r"(test|ruling)",
                label="a 'same cost' or 'constant time' requirement gets a test or a written ruling that it is not tested")

    def test_each_pinned_fix_is_observable_on_its_own(self):
        # Row 160
        line_in(self, self.text(), r"(each|every) fix", r"(on its own|only that fix|alone)", r"red",
                label="when a round pins several fixes for one rule, each case is red with only that fix removed")
        line_in(self, self.text(), r"(store|double)", r"increment", r"(model|semantic)",
                label="model each store semantic the code branches on (increment creating a key or not)")


class GateWriterPreflightAndHelpers(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-gate-writer")

    def test_a_gate_needing_redis_checks_the_project_has_it(self):
        # Row 164, gate writer half
        line_in(self, self.text(), r"redis", r"\.ddev/", r"add-on",
                label="preflight: a gate needing Redis checks .ddev/ for the add-on, never a resolving hostname")

    def test_shared_helpers_are_support_classes(self):
        # Row 168, gate writer half
        line_in(self, self.text(), r"helpers?", r"tests/Support", r"class",
                label="shared helpers are classes under tests/Support, never functions in another test file")
        line_in(self, self.text(), r"probe", r"harness", r"framework",
                label="probe the harness with a temporary, uncommitted framework-only test before handing over")


class BuilderRules(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-builder")

    def test_a_mutation_that_stays_green_may_have_a_second_guard(self):
        # Row 142
        line_in(self, self.text(), r"mutation", r"(second guard|two guards|another guard)", r"(disables|without|removes) the other",
                label="when a mutation stays green, look for a second guard and give each a test that disables the other")

    def test_existing_tests_may_get_environment_setup_for_a_new_requirement(self):
        # Row 161
        line_in(self, self.text(), r"existing", r"(environment|setup)", r"(no|never an?) assertion", r"hand-back",
                label="an existing test may get environment setup for a newly ruled requirement when no assertion changes, named in the hand-back")


class PlannerDevServices(unittest.TestCase):
    def test_a_dev_service_comes_with_a_slice_that_installs_it(self):
        # Row 164, planner half
        line_in(self, agent(self, "laravel-planner"), r"(dev(elopment)? service|service)", r"slice", r"install",
                label="an architecture decision naming a development service comes with a slice that installs it")


class DeepReviewer(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-reviewer-deep")

    def test_engine_behavior_can_be_proven_with_a_constant_select(self):
        # Row 146 (a)
        line_in(self, self.text(), r"(?-i:SELECT)", r"(constant|table-free)", r"(collation|engine|coercion|isolation)",
                label="a constant, table-free SELECT through the runner's database client proves engine behavior")

    def test_the_database_manual_counts_as_evidence(self):
        # Row 146 (b)
        line_in(self, self.text(), r"manual", r"(database|vendor)", r"URL",
                label="the database vendor's manual counts as a source, with the URL cited")

    def test_partly_maps_to_fail_when_the_brief_asks_pass_or_fail(self):
        # Row 147 (a)
        line_in(self, self.text(), r"partly", r"(?-i:\bFAIL\b)",
                label="when a brief asks PASS or FAIL, partly is FAIL with the met part named")

    def test_a_named_setup_commit_that_keeps_isolation_is_reported_as_reviewed(self):
        # Row 147 (b)
        line_in(self, self.text(), r"Test configuration: changed in", r"(kept|strengthened)",
                label="Test configuration: changed in <commit>, isolation kept or strengthened")

    def test_a_missing_checker_type_is_a_single_pass_reason(self):
        # Row 147 (c)
        line_in(self, self.text(), r"not registered", r"single[- ]pass", r"lenses?",
                label="'checker type not registered' is a single-pass reason; say which lenses the reviewer covered itself")

    def test_a_must_no_test_pins_is_an_important_finding(self):
        # Row 152, deep reviewer half
        line_in(self, self.text(), r"(?-i:\bMUST\b)", r"(no gate|no (builder )?test|not pinned|unpinned)", r"(?-i:Important)",
                label="each MUST of the slice that no gate or builder test pins is an Important finding")


if __name__ == "__main__":
    unittest.main()
