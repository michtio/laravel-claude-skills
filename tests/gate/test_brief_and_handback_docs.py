"""The brief format, the hand-back format and the outside-builder protocol, as standalone files any builder can read.

Requirements R18, R26, R27; acceptance criteria AC26 (the outside builder gets the brief file), AC27 (the
hand-back's lock-check lines), AC28 (an outside builder that exits with an error hands over to the next).
Contract: tests/OutsideBuilders/CONTRACT.md, section "Docs". Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_brief_and_handback_docs.py'
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import (  # noqa: E402
    BRIEF_DOC, BUILDERS_DOC, CALL_FORM, CLAUDE_ONLY_TOOLING, LOCK_COMMITTED, LOCK_TREE, NAMED_MODELS,
    PROFILE_DOC, assert_line, read_new,
)

BRIEF_FIELDS = ("Slice:", "Gate commit:", "Gate files:", "Pest command:", "Project root:", "Laravel version:")
HANDBACK_LINES = (
    "Gate flow: locked (<sha>)",
    "Lock check (committed): exit <n>",
    "Lock check (working tree): exit <n>",
    "R<n>: PASS|FAIL|PENDING",
    "Builder: <name>",
)


def docs_standalone(test: unittest.TestCase, text: str, name: str) -> None:
    for term in CLAUDE_ONLY_TOOLING:
        test.assertNotIn(term, text, f"{name} depends on assistant-only tooling: {term}")
    for term in NAMED_MODELS:
        test.assertIsNone(re.search(rf"(?i)(?<![a-z-]){re.escape(term)}(?![a-z-])", text), f"{name} names {term}")


class BriefFormat(unittest.TestCase):
    """R26, AC26: the brief a builder receives."""

    def text(self):
        return read_new(self, BRIEF_DOC)

    def test_the_brief_names_its_header_fields(self):
        text = self.text()
        for field in BRIEF_FIELDS:
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", text)

    def test_requirements_are_level_two_headings_with_their_criteria_verbatim(self):
        text = self.text()
        self.assertIn("## R<n>", text)
        assert_line(self, text, r"acceptance criteria", r"verbatim", label="each requirement with its acceptance criteria, verbatim")
        self.assertIn("## Pointers", text)
        self.assertIn("## Rules", text)

    def test_the_rules_section_lists_the_builder_rules(self):
        text = self.text()
        for rule in ("Never edit a gate file.", "Stop at a passing gate.", "At most 3 rounds.",
                     "Commit your work before writing the hand-back."):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_the_document_is_standalone(self):
        docs_standalone(self, self.text(), "docs/brief-format.md")


class HandbackFormat(unittest.TestCase):
    """R26, AC27: the hand-back a builder writes, and how it is checked."""

    def text(self):
        return read_new(self, BRIEF_DOC)

    def test_the_five_required_line_shapes_are_documented(self):
        text = self.text()
        for line in HANDBACK_LINES:
            with self.subTest(line=line):
                self.assertIn(line, text)

    def test_the_lock_check_lines_name_their_commands(self):
        text = self.text()
        self.assertIn(LOCK_COMMITTED, text)
        self.assertIn(LOCK_TREE, text)

    def test_a_hand_back_missing_a_line_does_not_count_as_a_pass(self):
        text = self.text()
        self.assertIn("handback_check.py --brief <brief-file> <handback-file>", text)
        assert_line(self, text, r"missing", r"(not count as a pass|never (counts as )?a pass|is not a pass)",
                    label="a hand-back that is missing a line does not count as a pass")

    def test_a_slice_passes_only_when_every_r_line_is_pass(self):
        assert_line(self, self.text(), r"every `?R<n>`?", r"`?PASS`?", r"only",
                    label="a slice passes only when every R<n> line is PASS")


class OutsideBuilderProtocol(unittest.TestCase):
    """R18, R27, AC26, AC28: how an outside builder is called and what its exit means."""

    def text(self):
        return read_new(self, BUILDERS_DOC)

    def test_the_builder_is_called_with_the_brief_file_and_the_hand_back_path(self):
        self.assertIn(CALL_FORM, self.text())

    def test_the_exit_codes_mean_done_unavailable_and_failed(self):
        text = self.text()
        assert_line(self, text, r"^\|\s*`?0`?\s*\|", r"done", label="| 0 | done")
        assert_line(self, text, r"^\|\s*`?3`?\s*\|", r"unavailable", r"next builder", label="| 3 | unavailable, next builder")
        assert_line(self, text, r"^\|\s*(any )?other", r"fail", r"next builder", label="| other | failed, next builder")

    def test_a_builder_that_outlives_its_timeout_counts_as_failed(self):
        assert_line(self, self.text(), r"`timeout_minutes`", r"(counts as )?failed",
                    label="no exit within timeout_minutes counts as failed")

    def test_builders_run_in_profile_order_and_the_package_builder_is_last(self):
        text = self.text()
        assert_line(self, text, r"order", r"skills-profile\.json|profile", label="builders run in the profile's order")
        assert_line(self, text, r"`laravel-builder`", r"same brief",
                    label="when every outside builder fails, laravel-builder builds the slice from the same brief")

    def test_the_result_is_checked_like_the_package_builders(self):
        text = self.text()
        self.assertIn(LOCK_COMMITTED, text)
        self.assertIn(LOCK_TREE, text)
        self.assertIn("handback_check.py", text)
        assert_line(self, text, r"3 rounds", label="at most 3 rounds per builder")

    def test_the_document_is_standalone(self):
        docs_standalone(self, self.text(), "docs/outside-builders.md")


class ProfileDoc(unittest.TestCase):
    """R18: the profile's builders example uses the documented call form."""

    def test_the_builders_example_matches_the_call_form(self):
        read_new(self, BUILDERS_DOC)
        text = read_new(self, PROFILE_DOC)
        self.assertFalse("{brief}" in text, "docs/profile.md still shows a {brief} placeholder; the call form appends the two paths")
        self.assertTrue("outside-builders.md" in text, "docs/profile.md does not point to docs/outside-builders.md")


if __name__ == "__main__":
    unittest.main()
