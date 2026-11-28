"""The stub outside builders behave exactly as their names say, under the documented protocol.

Requirements R18, R26, R27; acceptance criteria AC26 (stub-ok gets the brief file and its result passes the
lock check and the hand-back check), AC27 (stub-bad-handback's hand-back misses its lock-check lines and is
reported, not a pass), AC28 (stub-unavailable exits with the unavailable code and leaves nothing behind).
Each stub runs in a throwaway git copy of tests/Fixtures/outside-builders/gated-build with a gate commit, from
outside the project, so a commit in the project proves the stub read the brief's Project root.
Contract: tests/OutsideBuilders/CONTRACT.md, section "Stubs". Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_outside_builder_stubs.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import (  # noqa: E402
    BUILDERS_DOC, GatedCopy, assert_line, check, read_new, require_checker,
)


class StubUnavailable(unittest.TestCase):
    """AC28, R27."""

    def test_it_exits_with_the_unavailable_code_and_leaves_nothing_behind(self):
        assert_line(self, read_new(self, BUILDERS_DOC), r"^\|\s*`?3`?\s*\|", r"unavailable",
                    label="docs/outside-builders.md: | 3 | unavailable")
        with GatedCopy() as copy:
            proc = copy.run_stub("stub-unavailable")
            self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
            self.assertFalse(copy.handback.exists(), "stub-unavailable wrote a hand-back")
            self.assertEqual(copy.head(), copy.gate, "stub-unavailable committed")
            self.assertEqual(copy.status(), "", "stub-unavailable left files behind")


class StubOk(unittest.TestCase):
    """AC26, R18, R26."""

    def test_it_builds_from_the_brief_and_its_result_passes_the_lock_and_hand_back_checks(self):
        require_checker(self)
        with GatedCopy() as copy:
            proc = copy.run_stub("stub-ok")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(copy.subjects_after_gate(), ["feat(S1): greeting service (stub-ok)"])
            self.assertEqual(copy.lock_committed(), 0, "stub-ok changed a gate file")
            self.assertEqual(copy.status(), "", "stub-ok left uncommitted work")
            result = check(copy.brief, copy.handback)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            handback = copy.handback.read_text(encoding="utf-8")
            self.assertIn(f"Gate flow: locked ({copy.gate})", handback)
            self.assertIn("Lock check (committed): exit 0", handback)
            self.assertIn("Lock check (working tree): exit 0", handback)
            self.assertIn("R1: PASS", handback)
            self.assertIn("Builder: stub-ok", handback)


class StubBadHandback(unittest.TestCase):
    """AC27, R26."""

    def test_its_hand_back_misses_the_lock_check_lines_and_is_not_a_pass(self):
        require_checker(self)
        with GatedCopy() as copy:
            proc = copy.run_stub("stub-bad-handback")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            handback = copy.handback.read_text(encoding="utf-8")
            self.assertIn(f"Gate flow: locked ({copy.gate})", handback)
            self.assertIn("R1: ", handback)
            self.assertIn("Builder: stub-bad-handback", handback)
            self.assertNotIn("Lock check", handback)
            result = check(copy.brief, copy.handback)
            out = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, out)
            self.assertIn("missing line: Lock check (committed)", out)
            self.assertIn("missing line: Lock check (working tree)", out)


if __name__ == "__main__":
    unittest.main()
