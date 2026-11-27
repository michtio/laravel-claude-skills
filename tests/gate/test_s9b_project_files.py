"""Gate test for slice S9b (laravel-layer): the project-files rule (skills-gaps row 83, ruled by the owner).

Team rule: everything ships with README, docs, CHANGELOG and LICENSE where they apply, updated in every
slice that changes behavior. Boost's foundation line "only create documentation files if explicitly
requested" works against it, and nothing in the pack overrides it. Contract: tests/S9b/CONTRACT.md
section 12. Standard library only; no DDEV, no network.

Each rule is checked in ONE paragraph or bullet of the file it belongs to, by what an agent has to do,
not by a fixed sentence.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
GUIDELINES = REPO / "resources/boost/guidelines"
CHANGELOG = REPO / "CHANGELOG.md"
I = re.I
EM_DASH = chr(0x2014)
UK_SPELLING = re.compile(r"\b(behaviour|colour|organis\w+|licence|honour|favour|analys(e|ed|es|ing)\b|catalogue|initialis\w+)", I)


def strip_house_style(text: str) -> str:
    """Remove the `@if ($houseStyle)` block: a rule inside it would vanish when the profile switches house style off."""
    start = text.find("@if ($houseStyle)")
    if start == -1:
        return text
    depth = 0
    for m in re.finditer(r"@if\b|@endif\b", text[start:]):
        depth += 1 if m.group(0) == "@if" else -1
        if depth == 0:
            return text[:start] + text[start + m.end():]
    return text[:start]


def guideline_lines() -> list:
    lines = []
    for path in sorted(GUIDELINES.glob("*.blade.php")):
        text = path.read_text(encoding="utf-8")
        lines += [(path.name, l) for l in strip_house_style(text).splitlines()]
    return lines


def first(test: unittest.TestCase, lines: list, *patterns: str, label: str) -> str:
    for line in lines:
        if all(re.search(p, line, I) for p in patterns):
            return line
    test.fail(f"no single paragraph or bullet states: {label}")


def fenced_blocks(text: str) -> list:
    return re.findall(r"```[a-z]*\n(.*?)```", text, re.S)


class Guideline(unittest.TestCase):
    """A pack guideline, outside the house-style switch, states the project-files rule and that it wins."""

    def test_the_rule_names_the_four_files_and_when_they_are_updated(self):
        line = first(self, [l for _, l in guideline_lines()], r"README", r"CHANGELOG", r"LICENSE", r"\bdocs?\b",
                     label="README, docs, CHANGELOG and LICENSE ship with the project")
        self.assertRegex(line, r"(?i)where (they|it) applies?|when (they|it) applies?")
        self.assertRegex(line, r"(?i)(every|each|per) slice|slice that changes")

    def test_it_wins_over_boosts_explicitly_requested_line(self):
        line = first(self, [l for _, l in guideline_lines()], r"explicitly requested", r"(wins|takes precedence|overrides?|instead of|replaces?|does not apply)",
                     label="the rule wins over Boost's 'only create documentation files if explicitly requested'")
        self.assertRegex(line, r"(?i)boost")

    def test_it_is_a_pack_guideline_that_survives_house_style_off(self):
        text = "\n".join(l for _, l in guideline_lines())
        self.assertRegex(text, r"CHANGELOG", "the rule must sit outside the house-style block of core.blade.php, or in its own file")

    def test_it_tells_the_agent_not_to_wait_for_a_request(self):
        first(self, [l for _, l in guideline_lines()], r"CHANGELOG", r"(without|no need|not wait|never wait|do not wait|don't wait|need not)[^.]{0,80}(ask|request)",
              label="an agent updates the project files without waiting to be asked")


class Builder(unittest.TestCase):
    def text(self):
        return s8.read_agent(self, "laravel-builder")

    def test_a_step_updates_readme_and_changelog_for_the_slice_before_hand_back(self):
        line = first(self, self.text().splitlines(), r"README", r"CHANGELOG", r"slice", r"(update|updates|updated)", r"(before|ahead of)[^.]{0,80}(hand-back|hand back|checker)",
                     label="before the hand-back the builder updates the README and the CHANGELOG for the slice")
        self.assertRegex(line, r"(?i)(behavior|user-facing|public)")

    def test_the_step_overrides_boosts_documentation_line(self):
        first(self, self.text().splitlines(), r"explicitly requested", r"boost", r"(README|CHANGELOG|project files)",
              label="the builder does not treat Boost's 'only create documentation files if explicitly requested' as a reason to skip them")

    def test_the_step_is_in_the_build_sequence_not_only_in_a_rule(self):
        t = self.text()
        build = re.search(r"^## (Build|Project files|Simplification pass)", t, re.M)
        self.assertIsNotNone(build)
        self.assertRegex(t, r"(?m)^## (Project files|Docs and changelog|Project files and changelog)\s*$|After all gates pass[^\n]{0,400}(README|CHANGELOG)|After the layers:[^\n]{0,500}(README|CHANGELOG)",
                         "a named section, or a step in the after-the-layers sequence")

    def test_the_hand_back_reports_the_project_files(self):
        block = next(b for b in fenced_blocks(self.text()) if "Gate flow:" in b and "Built:" in b)
        line = next((l for l in block.splitlines() if l.startswith("Project files:")), "")
        self.assertRegex(line, r"(?i)README")
        self.assertRegex(line, r"(?i)CHANGELOG")
        self.assertRegex(line, r"(?i)(none|not apply|n/a)", "a slice that changes nothing user-facing says why no file changed")


class Checker(unittest.TestCase):
    def text(self):
        return s8.read_agent(self, "laravel-review-checker")

    def test_the_conventions_lens_checks_readme_changelog_and_docs(self):
        line = first(self, self.text().splitlines(), r"README", r"CHANGELOG", r"(behavior|user-facing)", r"(diff|slice)",
                     label="the checker flags a diff that changes behavior without the README, docs and CHANGELOG update")
        self.assertRegex(line, r"(?i)\bdocs?\b")

    def test_a_missing_update_is_an_important_finding(self):
        first(self, self.text().splitlines(), r"CHANGELOG", r"Important",
              label="a missing project-files update is an Important finding")

    def test_the_lens_is_the_conventions_one(self):
        t = self.text()
        m = re.search(r"- \*\*conventions\*\*:(.*?)(?=\n- \*\*|\n\n|\Z)", t, re.S)
        self.assertIsNotNone(m, "no conventions lens line")
        self.assertRegex(m.group(1), r"CHANGELOG", "the item belongs to the conventions lens, which runs on every 50-line diff")


class PackChangelog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.is_file() else None

    def need(self):
        self.assertIsNotNone(self.text, "CHANGELOG.md is missing at the repo root")
        return self.text

    def test_it_exists_with_a_title(self):
        self.assertRegex(self.need(), r"\A# Changelog\b")

    def test_it_has_an_unreleased_section_with_entries(self):
        t = self.need()
        m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## |\Z)", t, re.S | re.M)
        self.assertIsNotNone(m, "no '## [Unreleased]' section")
        self.assertRegex(m.group(1), r"(?m)^- \S", "the Unreleased section lists what the pack ships so far")

    def test_it_is_ready_for_the_first_release(self):
        self.assertIn("1.0.0-beta.1", self.need())

    def test_it_follows_keep_a_changelog_headings(self):
        t = self.need()
        m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## |\Z)", t, re.S | re.M)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"(?m)^### (Added|Changed|Fixed)\b")

    def test_license_ships_too(self):
        self.assertTrue((REPO / "LICENSE").is_file())


class Style(unittest.TestCase):
    """US spelling and no em dashes in what this slice adds."""

    def files(self):
        out = [REPO / "CHANGELOG.md"] + sorted(GUIDELINES.glob("*.blade.php"))
        out += [REPO / "agents/laravel-builder.md", REPO / "agents/laravel-review-checker.md", REPO / "agents/laravel-gate-writer.md", REPO / "README.md", REPO / "docs/profile.md"]
        return [p for p in out if p.is_file()]

    def test_no_em_dash(self):
        for p in self.files():
            with self.subTest(file=p.name):
                self.assertNotIn(EM_DASH, p.read_text(encoding="utf-8"))

    def test_us_spelling(self):
        for p in self.files():
            with self.subTest(file=p.name):
                self.assertIsNone(UK_SPELLING.search(p.read_text(encoding="utf-8")), f"{p.name} uses a UK spelling")

    def test_the_changelog_exists_to_be_checked(self):
        self.assertTrue(CHANGELOG.is_file(), "CHANGELOG.md is missing")


if __name__ == "__main__":
    unittest.main()
