"""The hand-back checker: an outside builder's hand-back is checked for its required lines before the checker runs.

Requirement R26; acceptance criterion AC27 ("Given an outside hand-back missing its lock-check line, when the
gated build reads it, then the build reports the missing line and does not count it as a pass").
Contract: tests/OutsideBuilders/CONTRACT.md, section "Hand-back checker". Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_handback_check.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import (  # noqa: E402
    CHECK_SH, HANDBACKS, check, read_new, rel, require_checker, run_checker,
)

BRIEF = HANDBACKS / "brief.md"

# fixture -> (brief, substring the output must contain); every one exits 1.
REJECTED = {
    "missing-gate-flow.md": ("brief.md", "missing line: Gate flow"),
    "missing-r-line.md": ("brief.md", "missing line: R5"),
    "bad-status.md": ("brief.md", "bad status: R2"),
    "missing-builder.md": ("brief.md", "missing line: Builder"),
    "lock-nonzero.md": ("brief.md", "gate touched"),
    "flow-downgrade.md": ("brief.md", "bad line: Gate flow"),
    "wrong-sha.md": ("brief.md", "bad line: Gate flow"),
    "dup-r.md": ("brief.md", "duplicate line: R2"),
    "dup-lock.md": ("brief.md", "duplicate line: Lock check (working tree)"),
    "dup-flow.md": ("brief.md", "duplicate line: Gate flow"),
    "fenced.md": ("brief.md", "missing line: Gate flow"),
    "unknown-r.md": ("brief.md", "unknown line: R9"),
}

# (brief, hand-back) pairs that are well formed; each exemption is paired with a rejected case above.
ACCEPTED = [
    ("brief.md", "complete.md"),
    ("brief.md", "complete-bom.md"),
    ("brief-none.md", "complete-builder-written.md"),  # paired: flow-downgrade.md (lock lines need a gate commit)
    ("brief-fenced-example.md", "complete.md"),  # paired: fenced.md (fenced lines never count)
]


class MissingLockCheckLine(unittest.TestCase):
    """AC27, R26."""

    def test_a_hand_back_missing_its_working_tree_lock_line_is_reported_and_not_a_pass(self):
        require_checker(self)
        proc = check(BRIEF, HANDBACKS / "missing-lock-line.md")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("missing line: Lock check (working tree)", proc.stdout + proc.stderr)

    def test_a_hand_back_missing_its_committed_lock_line_is_reported_and_not_a_pass(self):
        require_checker(self)
        proc = check(BRIEF, HANDBACKS / "missing-committed-lock-line.md")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("missing line: Lock check (committed)", proc.stdout + proc.stderr)

    def test_a_hand_back_with_no_lock_lines_reports_both(self):
        require_checker(self)
        proc = check(BRIEF, HANDBACKS / "missing-both-lock-lines.md")
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("missing line: Lock check (committed)", out)
        self.assertIn("missing line: Lock check (working tree)", out)


class RequiredLines(unittest.TestCase):
    """R26: gate flow, lock check exit codes and per-R-id status are each checked."""

    def test_a_complete_hand_back_is_well_formed(self):
        require_checker(self)
        for brief, handback in ACCEPTED:
            with self.subTest(brief=brief, handback=handback):
                proc = check(HANDBACKS / brief, HANDBACKS / handback)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_each_missing_bad_or_duplicated_line_is_rejected_with_its_reason(self):
        require_checker(self)
        for handback, (brief, needle) in REJECTED.items():
            with self.subTest(handback=handback):
                proc = check(HANDBACKS / brief, HANDBACKS / handback)
                out = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 1, out)
                self.assertIn(needle, out)

    def test_every_fixture_is_classified(self):
        require_checker(self)
        briefs = {"brief.md", "brief-none.md", "brief-fenced-example.md"}
        known = set(REJECTED) | {h for _, h in ACCEPTED} | briefs | {
            "missing-lock-line.md", "missing-committed-lock-line.md", "missing-both-lock-lines.md"}
        on_disk = {p.name for p in HANDBACKS.glob("*.md")}
        self.assertTrue(on_disk, "no hand-back fixtures found")
        self.assertEqual(on_disk, known)


class UsageErrors(unittest.TestCase):
    """R26: a broken call is a usage error (exit 2), never a pass and never a form failure."""

    def test_bad_calls_exit_2(self):
        require_checker(self)
        cases = {
            "no arguments": (),
            "no --brief": (str(HANDBACKS / "complete.md"),),
            "missing hand-back file": ("--brief", str(BRIEF), str(HANDBACKS / "does-not-exist.md")),
            "brief with no R ids": ("--brief", str(HANDBACKS / "complete.md"), str(HANDBACKS / "complete.md")),
        }
        for label, args in cases.items():
            with self.subTest(case=label):
                proc = run_checker(*args)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


class PackageCheck(unittest.TestCase):
    """AC27 in the plan's verification gate: scripts/check.sh fails the checker on the missing-line fixture."""

    def test_check_sh_runs_the_checker_on_its_fixtures(self):
        require_checker(self)
        text = read_new(self, CHECK_SH)
        lines = text.splitlines()
        missing = rel(HANDBACKS / "missing-lock-line.md")
        complete = rel(HANDBACKS / "complete.md")
        self.assertTrue(
            any(l.lstrip().startswith("must_fail") and "scripts/handback_check.py" in l and missing in l
                and "missing line: Lock check (working tree)" in l for l in lines),
            f"scripts/check.sh has no must_fail line running scripts/handback_check.py on {missing}")
        self.assertTrue(
            any(l.lstrip().startswith("gate") and "scripts/handback_check.py" in l and complete in l for l in lines),
            f"scripts/check.sh has no gate line running scripts/handback_check.py on {complete}")


if __name__ == "__main__":
    unittest.main()
