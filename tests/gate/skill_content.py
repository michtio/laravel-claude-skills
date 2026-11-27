"""Shared helpers for the skill content gates: pitfalls, testing notes, verdict rows and agent rules.

Contract: tests/SkillContent/CONTRACT.md. Standard library only; no DDEV, no network.

A rule counts only when ONE paragraph or bullet (one line of the file) carries it by its operative
words, as in the earlier agent and docs gates: a keyword somewhere in the file does not count.

Where content lands decides what else it must carry:
- laravel-pitfalls references (R1, R2): the file has a Gap line, and the reference's section in the
  git-ignored internal-docs/pitfall-sources.md cites the gaps row (`skills-gaps row 101`, or
  `skills-gaps rows 119, 120 and 151`). The source half runs where internal-docs/ exists (the
  builder's and the reviewer's checkout); a public clone or CI has no internal-docs/.
- testing notes: one place, laravel-pitfalls/references/testing.md (owner ruling: no new skill), with its
  Gap line and a `## testing` source section citing each row.
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as agents  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
SKILLS = REPO / "resources/boost/skills"
PITFALL_REFS = SKILLS / "laravel-pitfalls/references"
TESTING = PITFALL_REFS / "testing.md"
REGISTER = SKILLS / "laravel-package-verdicts/references/register.md"
CORE = REPO / "resources/boost/guidelines/core.blade.php"
SOURCES = REPO / "internal-docs/pitfall-sources.md"
I = re.I

GAP = re.compile(r"^Gap: (not covered by Boost|covered partly by Boost \(\S.*\))\s*$", re.MULTILINE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def files(scope: str) -> list:
    """The Markdown files a scope covers: 'pitfalls' (the pitfall references) or 'skills' (every shipped skill file)."""
    if scope == "pitfalls":
        return sorted(PITFALL_REFS.glob("*.md"))
    if scope == "skills":
        return sorted(SKILLS.rglob("*.md"))
    raise ValueError(scope)


def first_line(paths: list, patterns: tuple):
    """(path, line) of the first line, over the files in order, that matches every pattern; None when none does."""
    for path in paths:
        for line in read(path).splitlines():
            if all(re.search(p, line, I) for p in patterns):
                return path, line
    return None


def line_in(test: unittest.TestCase, text: str, *patterns: str, label: str) -> str:
    for line in text.splitlines():
        if all(re.search(p, line, I) for p in patterns):
            return line
    test.fail(f"no single paragraph or bullet states: {label}")


def section(text: str, heading: str) -> str:
    """The body of a level-2 section whose heading starts with `heading`, up to the next level-2 heading."""
    m = re.search(rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def cites_row(line: str, row: int) -> bool:
    return re.search(rf"skills-gaps rows? (?:\d+(?:,? and |, ))*{row}\b", line) is not None


def assert_sourced(test: unittest.TestCase, path: Path, *, row: int | None = None, source: str | None = None) -> None:
    """R2: the pitfall's reference section in internal-docs/pitfall-sources.md cites its finding."""
    if not SOURCES.is_file():
        return  # git-ignored: absent in a public clone and in CI (see the module docstring)
    body = section(read(SOURCES), path.stem)
    test.assertTrue(body, f"internal-docs/pitfall-sources.md has no `## {path.stem}` section for {path.name}")
    lines = body.splitlines()
    if row is not None:
        test.assertTrue(any(cites_row(l, row) for l in lines),
                        f"pitfall-sources.md `## {path.stem}` has no source line citing skills-gaps row {row}")
    if source is not None:
        test.assertTrue(any(source in l for l in lines),
                        f"pitfall-sources.md `## {path.stem}` has no source line citing {source}")


def pitfall(test: unittest.TestCase, row: int | None, *patterns: str, label: str, source: str | None = None) -> str:
    """One line of a laravel-pitfalls reference carries the item; the reference has a gap line and a source line."""
    found = first_line(files("pitfalls"), patterns)
    if found is None:
        test.fail(f"no laravel-pitfalls reference has a paragraph or bullet that states: {label}")
    path, line = found
    test.assertRegex(read(path), GAP, f"{path.name} carries the item but no Gap: line (R1)")
    assert_sourced(test, path, row=row, source=source)
    return line


def note(test: unittest.TestCase, *patterns: str, label: str, row: int) -> str:
    """One line of laravel-pitfalls/references/testing.md carries the testing note (owner ruling: no new skill,
    one place); the file has a Gap line (R1) and its `## testing` source section cites the row (R2)."""
    found = first_line([TESTING], patterns)
    if found is None:
        test.fail(f"laravel-pitfalls/references/testing.md has no paragraph or bullet that states: {label}")
    path, line = found
    test.assertRegex(read(path), GAP, "testing.md carries the note but no Gap: line (R1)")
    assert_sourced(test, path, row=row)
    return line


def house_style_block(text: str) -> str:
    """The body of the core guideline's `@if ($houseStyle)` block, or '' when there is none."""
    m = re.search(r"@if \(\$houseStyle\)(.*?)@endif", text, re.S)
    return m.group(1) if m else ""


def agent(test: unittest.TestCase, stem: str) -> str:
    return agents.read_agent(test, stem)


def register_row(package: str) -> list:
    """The cells of the register row for a package, or [] when it has none."""
    for line in read(REGISTER).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].strip("`") == package:
            return cells
    return []


def assert_verdict(test: unittest.TestCase, package: str, uses: tuple, *needles: str) -> list:
    """A five-cell register row with a use from `uses`, every needle in Reason or Conditions, checked on or after 2026-11-27."""
    cells = register_row(package)
    test.assertTrue(cells, f"register.md has no row for {package}")
    test.assertEqual(len(cells), 5, f"the {package} row must have the five columns")
    test.assertIn(cells[1], uses, f"{package}: Use is {cells[1]!r}")
    for needle in needles:
        test.assertRegex(cells[2] + " " + cells[3], needle, f"{package}: Reason or Conditions must state {needle!r}")
    test.assertGreaterEqual(date.fromisoformat(cells[4]), date(2026, 11, 27))
    return cells
