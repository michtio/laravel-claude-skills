"""Human-readable tests: files named by feature, descriptions as sentences, R and AC ids as Pest groups,
no slice or round ids in names, gates run by group, unique helper prefixes per file.

Requirements R7, R17 (decisions log 2026-11-27: "Human-readable tests", pinned for the gate writer, the
builder and the testing skill). Gaps rows 158, 162 and 163.
Contract: tests/SkillContent/CONTRACT.md, section "Readable test names".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import agent, agents, first_line, line_in, note  # noqa: E402

FEATURE_FILE = (r"\bfiles?\b", r"\bnamed? (by|after) (the |its )?feature")
SENTENCE = (r"descriptions?", r"sentences?")
GROUPS = (r"->group\(", r"\b(R\d+|AC\d+|R and AC)\b")
NO_PROCESS_IDS = (r"\bnever\b", r"\bslice\b", r"\bround\b", r"\bfile\b", r"\bhelper\b", r"\bclass\b", r"\bconstant\b", r"\bcomment\b")
GROUP_GATE = (r"--group=",)
HELPER_PREFIX = (r"helper", r"prefix", r"(unique|per.file|each file|its own file|own file)")


class GateWriter(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-gate-writer")

    def test_files_are_named_by_feature_not_by_slice(self):
        self.assertNotIn("<Slice>GateTest", self.text(), "Method 3 still names the file after the slice")
        line_in(self, self.text(), *FEATURE_FILE, label="test files are named by feature")

    def test_descriptions_read_as_sentences_with_ids_in_groups(self):
        line_in(self, self.text(), *SENTENCE, label="test descriptions read as sentences")
        line_in(self, self.text(), *GROUPS, label="R and AC ids go in Pest groups: ->group('R8', 'AC8')")
        self.assertNotRegex(self.text(), r"(?i)criterion id in the test name",
                            "the criterion id goes in a group, not in the test name")

    def test_no_slice_or_round_id_in_any_name(self):
        line_in(self, self.text(), *NO_PROCESS_IDS,
                label="never a slice or round id in a file, helper, class, constant or comment name")
        self.assertNotRegex(self.text(), r"(?i)prefix each with the slice id",
                            "named classes are still prefixed with the slice id")

    def test_gates_run_by_group_and_helpers_have_a_unique_prefix(self):
        line_in(self, self.text(), *GROUP_GATE, label="a gate is run as --group=<id>, not a word filter")
        line_in(self, self.text(), *HELPER_PREFIX, label="global helper functions carry a prefix unique to their file")

    def test_a_rename_only_gate_commit_moves_the_lock(self):
        # Row 158: may sit in the gate writer or the builder
        found = first_line([agents.agent_path("laravel-gate-writer"), agents.agent_path("laravel-builder")],
                           (r"rename", r"(git diff -M|git show -M|-M\b)", r"lock"))
        self.assertIsNotNone(found, "no agent says a rename-only gate commit (assertions unchanged, git diff -M) moves the lock")


class Builder(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-builder")

    def test_the_builders_own_tests_follow_the_same_names(self):
        line_in(self, self.text(), *FEATURE_FILE, label="the builder's own test files are named by feature")
        line_in(self, self.text(), *SENTENCE, label="descriptions read as sentences")
        line_in(self, self.text(), *GROUPS, label="R and AC ids go in Pest groups")
        line_in(self, self.text(), *NO_PROCESS_IDS,
                label="never a slice or round id in a file, helper, class, constant or comment name")

    def test_the_builder_runs_gates_by_group(self):
        line_in(self, self.text(), *GROUP_GATE, label="the builder runs a gate as --group=<id>")


class Planner(unittest.TestCase):
    def text(self):
        return agent(self, "laravel-planner")

    def test_verification_gates_are_written_as_groups(self):
        # Row 162
        line_in(self, self.text(), r"--group=", r"(word|filter|description)",
                label="write verification gates as --group=AC8 (or a file path), not a word filter that depends on description prefixes")
        self.assertNotIn("--filter=StaffLoginGateTest", self.text(), "the plan format example still gates on a slice-named filter")


class TestingSkill(unittest.TestCase):
    def test_the_testing_notes_carry_the_naming_rules(self):
        # Rows 158, 162
        note(self, *FEATURE_FILE, label="test files are named by feature")
        note(self, *SENTENCE, label="descriptions read as sentences")
        note(self, *GROUPS, label="R and AC ids go in Pest groups")
        note(self, *NO_PROCESS_IDS, label="never a slice or round id in a file, helper, class, constant or comment name")
        note(self, *HELPER_PREFIX, label="global helper functions carry a prefix unique to their file")

    def test_groups_are_runnable_selectors(self):
        # Row 163
        note(self, r"--list-tests", r"--group", label="--list-tests --group=AC8 lists exactly the grouped tests")
        note(self, r"--group=", r"(word|filter|description)",
             label="run gates as --group=<id>, not a word filter that depends on description prefixes")
        note(self, r"->group\(", r"(anywhere|->with\(|->throws\()",
             label="->group() chains anywhere on a test, before ->with() or ->throws()")

    def test_renames_and_splits(self):
        # Row 163
        note(self, r"rename", r"(only|just) the (description|test\(\))", r"closing",
             label="a rename script changes only the description line and the closing line of each test")
        note(self, r"split", r"helpers?", r"(together|with its|redeclare)",
             label="split a gate file only together with its helpers (a second definition is a fatal redeclare)")


if __name__ == "__main__":
    unittest.main()
