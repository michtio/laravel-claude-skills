"""The skill and the user docs state the trust list and the hidden-character rules (R18, R27).

Decisions log 2026-11-28 ("consent once per machine") and skills-gaps row 240 (S10 round 3 follow-ups).
A rule counts only when one line (one paragraph or bullet) carries it. Pinned:

- laravel-gated-build step 1.2 states what builders_check refuses as it does: Unicode control and format
  characters and line or paragraph separators, not only "a control character" (row 240, item 1);
- step 1.7: `builder_trust.py check` prints the list with trusted builders marked `(trusted)`; trusted
  commands skip the prompt, in a non-interactive run too; after an explicit yes `builder_trust.py add`
  records each confirmed builder; builders run from the file `builder_trust.py check --out` wrote;
- docs/outside-builders.md: where the trust file lives and its overrides, what the identity is, that any
  change asks again, that a trust file inside the project is ignored, and how to revoke an entry;
- docs/profile.md: the outside-builders section points at the trust list and its revoke command, and the
  extra-steps section says steps refuse right-to-left overrides, zero-width characters and separators.

Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_consent_texts.py'
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import BUILDERS_DOC, PROFILE_DOC, SKILL, assert_line, read_new  # noqa: E402


def section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


class SkillStep12(unittest.TestCase):
    """Row 240, item 1: step 1.2 matches what builders_check.py refuses."""

    def test_step_1_2_names_unicode_control_format_and_separator_characters(self):
        text = read_new(self, SKILL)
        lines = [l for l in text.splitlines() if "builders_check.py --profile" in l]
        self.assertEqual(len(lines), 1, "step 1.2 is the one line that runs builders_check.py --profile")
        line = lines[0]
        self.assertRegex(line, r"Unicode control")
        self.assertRegex(line, r"format")
        self.assertRegex(line, r"line or paragraph separator")
        self.assertNotRegex(line, r"holds a control character")


class SkillStep17(unittest.TestCase):
    """Ruling 2026-11-28: consent once per machine, in the skill's confirmation step."""

    def setUp(self):
        self.text = read_new(self, SKILL)

    def test_the_printed_list_marks_trusted_builders(self):
        assert_line(self, self.text, r"builder_trust\.py check", r"\(trusted\)",
                    label="builder_trust.py check prints the list with trusted builders marked (trusted)")

    def test_trusted_commands_skip_the_prompt_in_a_non_interactive_run_too(self):
        assert_line(self, self.text, r"trusted", r"skip(s)? the prompt|without asking", r"non-interactive",
                    label="trusted commands skip the prompt, in a non-interactive run too")

    def test_an_explicit_yes_is_recorded_with_builder_trust_add(self):
        assert_line(self, self.text, r"builder_trust\.py add", r"yes",
                    label="after an explicit yes, builder_trust.py add records each confirmed builder")

    def test_builders_run_from_the_file_the_trust_check_wrote(self):
        m = re.search(r"builder_trust\.py check[^\n`]*--out (<work>/\S+?)[`\s]", self.text)
        self.assertIsNotNone(m, "the skill runs builder_trust.py check with --out <work>/<file>")
        run_it = [l for l in self.text.splitlines() if l.startswith("**Run it:**")]
        self.assertEqual(len(run_it), 1, "one **Run it:** line")
        self.assertIn(f"--builders {m.group(1)}", run_it[0], "run_builder.py runs from the trust check's file")


class BuildersDoc(unittest.TestCase):
    """docs/outside-builders.md states the trust list in full."""

    def setUp(self):
        self.text = read_new(self, BUILDERS_DOC)

    def test_where_the_trust_file_lives(self):
        assert_line(self, self.text, re.escape("~/.config/laravel-claude-skills/trusted-builders.json"),
                    r"XDG_CONFIG_HOME", r"LARAVEL_CLAUDE_SKILLS_TRUST_FILE",
                    label="the default trust file, XDG_CONFIG_HOME and LARAVEL_CLAUDE_SKILLS_TRUST_FILE")

    def test_what_a_trusted_entry_is_keyed_on(self):
        assert_line(self, self.text, r"top-level", r"origin", r"name", r"command", r"timeout",
                    label="an entry is keyed on the git top-level, the origin URL, the name, command and timeout")

    def test_trusted_builders_run_unattended_and_any_change_asks_again(self):
        assert_line(self, self.text, r"trusted", r"without asking|skip(s)? the prompt", r"unattended|non-interactive",
                    label="a trusted builder runs without asking, unattended too")
        assert_line(self, self.text, r"one character", r"timeout", r"asks? again",
                    label="a command differing by one character or a changed timeout asks again")

    def test_a_trust_file_inside_the_project_is_ignored(self):
        assert_line(self, self.text, r"trust file", r"inside the project", r"ignored",
                    label="a trust file inside the project is ignored")

    def test_how_to_revoke_an_entry(self):
        assert_line(self, self.text, r"builder_trust\.py remove", r"--root", r"--name",
                    label="revoke with builder_trust.py remove --root <project root> --name <name>")


class ProfileDoc(unittest.TestCase):
    def setUp(self):
        self.text = read_new(self, PROFILE_DOC)

    def test_the_outside_builders_section_points_at_the_trust_list(self):
        body = section(self.text, "Outside builders")
        self.assertTrue(body, "docs/profile.md has no ## Outside builders section")
        assert_line(self, body, r"trusted|trust list", r"once per machine", r"builder_trust\.py remove",
                    label="profile.md: the yes is kept once per machine, revoked with builder_trust.py remove")

    def test_extra_steps_refuse_hidden_unicode_characters(self):
        body = section(self.text, "Extra setup steps")
        self.assertTrue(body, "docs/profile.md has no ## Extra setup steps section")
        assert_line(self, body, r"right-to-left", r"zero-width", r"separator",
                    label="extra steps refuse right-to-left overrides, zero-width characters and separators")


if __name__ == "__main__":
    unittest.main()
