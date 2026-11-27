"""Gate test for slice S9c (laravel-layer): the owner's rules that ship inside the agents.

Decisions log 2026-11-27 ("found defects are fixed, never deferred" and "project files on everything"
ship inside the pack's agents) and the owner's learnings ruling for this slice. Requirements R15, R17.
Contract: tests/S9c/CONTRACT.md section 5. Standard library only; no DDEV, no network.

- The builder, both reviewers, the checker and the debugger fix a found defect in the slice, or raise
  it with the owner, and never mark it later or out of scope.
- Every brief (slice) the planner writes carries that rule and a Project files line.
- Learnings come in two kinds (gaps in the agent or skill rules; stack learnings with evidence), and
  every hand-back lists the learnings it recorded, or says none.

Each rule is checked in ONE paragraph or bullet of the file it belongs to.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from test_s9b_agents import fenced_blocks, one_line, section  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
I = re.I
EM_DASH = chr(0x2014)
UK_SPELLING = re.compile(r"\b(behaviour|colour|organis\w+|licence|honour|favour|analys(e|ed|es|ing)\b|catalogue|initialis\w+|recognis\w+|summaris\w+|prioritis\w+|authoris\w+)", I)

ALL = ("laravel-planner", "laravel-gate-writer", "laravel-builder", "laravel-review-checker",
       "laravel-reviewer", "laravel-reviewer-deep", "laravel-debugger")
DEFECT_AGENTS = ("laravel-builder", "laravel-reviewer", "laravel-reviewer-deep", "laravel-review-checker", "laravel-debugger")
DEFERRAL = r"(later|out of scope|follow-up|follow up|separate change|future slice|defer)"


def text(stem: str) -> str:
    return s8.agent_path(stem).read_text(encoding="utf-8")


class FoundDefects(unittest.TestCase):
    def test_each_agent_fixes_or_raises_a_found_defect_and_never_defers_it(self):
        for stem in DEFECT_AGENTS:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"defect", rf"(never|not)\b[^.]{{0,80}}{DEFERRAL}",
                                label=f"{stem}: a found defect is fixed in the slice or raised with the owner, never marked later or out of scope")
                self.assertRegex(line, r"(?i)\b(fix|fixed|finding)\b")
                self.assertRegex(line, r"(?i)(owner|raise|report)")

    def test_the_writing_agents_raise_with_the_owner_when_they_do_not_fix(self):
        for stem in ("laravel-builder", "laravel-debugger"):
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"defect", r"owner", r"\bfix",
                                label=f"{stem}: fix the found defect in the slice, or raise it with the owner")
                self.assertRegex(line, r"(?i)(slice|change|regression test|test)")

    def test_no_agent_tells_itself_to_leave_a_found_bug_for_later(self):
        bad = re.compile(r"(leave|leaving)[^.\n]{0,60}\b(bugs?|defects?)\b[^.\n]{0,80}(separate|later|follow|another)", I)
        for stem in DEFECT_AGENTS:
            with self.subTest(agent=stem):
                self.assertNotRegex(text(stem), bad)


class PlannerBriefs(unittest.TestCase):
    def template(self) -> str:
        blocks = [b for b in fenced_blocks(text("laravel-planner")) if "**Deliverable:**" in b]
        if not blocks:
            self.fail("the planner's slice template is missing")
        return blocks[0]

    def test_the_slice_template_has_a_project_files_line(self):
        self.assertRegex(self.template(), r"(?m)^- \*\*Project files:\*\*")

    def test_the_slice_template_carries_the_found_defect_rule(self):
        line = one_line(self, self.template(), r"defect", rf"(never|not)\b[^.]{{0,80}}{DEFERRAL}",
                        label="the slice template carries: found defects are fixed in the slice or raised with the owner, never deferred")
        self.assertRegex(line, r"(?i)owner")

    def test_a_planner_rule_says_every_slice_carries_both(self):
        line = one_line(self, section(text("laravel-planner"), "Rules"), r"(every|each) (slice|brief)", r"Project files", r"defect",
                        label="every slice (brief) the planner writes carries the found-defect rule and a Project files line")


class Learnings(unittest.TestCase):
    def test_each_agent_records_learnings_in_two_kinds(self):
        for stem in ALL:
            with self.subTest(agent=stem):
                line = one_line(self, text(stem), r"learnings?", r"\bgaps?\b", r"\bstack\b",
                                label=f"{stem}: learnings in two kinds, gaps in the agent or skill rules and stack learnings with evidence")
                self.assertRegex(line, r"(?i)(agent|skill)")
                self.assertRegex(line, r"(?i)evidence")
                self.assertRegex(line, r"(?i)\bnone\b", "the hand-back says none when nothing was learned")

    def test_each_hand_back_has_a_learnings_line(self):
        for stem in ALL:
            with self.subTest(agent=stem):
                self.assertRegex(text(stem), r"(?m)^Learnings: |`Learnings: ",
                                 "the hand-back or report carries a Learnings: line")

    def test_the_fenced_hand_backs_carry_the_line(self):
        cases = {
            "laravel-gate-writer": "Gate commit:",
            "laravel-builder": "Built:",
            "laravel-debugger": "Root cause:",
            "laravel-reviewer": "### Critical",
        }
        for stem, marker in cases.items():
            with self.subTest(agent=stem):
                block = next((b for b in fenced_blocks(text(stem)) if marker in b), "")
                self.assertRegex(block, r"(?m)^Learnings: ")


class ProjectFiles(unittest.TestCase):
    """Plan S9c, Project files: README agents section; CHANGELOG entry under Unreleased."""

    def readme_agents(self) -> str:
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        return section(readme, "Agents")

    def unreleased(self) -> str:
        changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
        return section(changelog, "[Unreleased]")

    def test_readme_agents_section_states_the_found_defect_rule(self):
        one_line(self, self.readme_agents(), r"defect", rf"(never|not)\b[^.]{{0,80}}{DEFERRAL}",
                 label="README Agents: found defects are fixed or raised, never deferred")

    def test_readme_agents_section_states_the_learnings(self):
        one_line(self, self.readme_agents(), r"learnings?", r"\bgaps?\b", r"\bstack\b",
                 label="README Agents: every hand-back lists its learnings in two kinds")

    def test_changelog_unreleased_has_the_s9c_entry(self):
        one_line(self, self.unreleased(), r"defect", r"learnings?",
                 label="CHANGELOG Unreleased: an entry for the found-defect rule and the learnings line")


class Wording(unittest.TestCase):
    """US spelling and no em dashes in what this slice touches (green today; the builder keeps it)."""

    def test_agent_files_readme_and_changelog(self):
        paths = [s8.agent_path(stem) for stem in ALL] + [REPO / "README.md", REPO / "CHANGELOG.md"]
        for path in paths:
            with self.subTest(path=path.name):
                body = path.read_text(encoding="utf-8")
                self.assertNotIn(EM_DASH, body)
                prose = re.sub(r"`[^`\n]*`", "", re.sub(r"```.*?```", "", body, flags=re.S))  # commands such as `phpstan analyse` are not prose
                found = UK_SPELLING.search(prose)
                self.assertIsNone(found, found and found.group(0))


if __name__ == "__main__":
    unittest.main()
