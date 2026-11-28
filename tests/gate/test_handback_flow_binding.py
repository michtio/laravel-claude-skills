"""The hand-back checker binds the Gate flow line to the brief's `Gate commit:` in both directions.

Requirement R26 (the hand-back's gate flow line is checked before the checker runs). Builder-added test (G3),
beside the S10 gate: the gate proves a locked brief rejects a builder-written flow (flow-downgrade.md); this
proves a brief with `Gate commit: none` rejects a locked flow, which would otherwise make up a gate commit.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_handback_flow_binding.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import HANDBACKS, check, require_checker  # noqa: E402


class FlowBinding(unittest.TestCase):
    """R26."""

    def test_a_brief_without_a_gate_commit_rejects_a_locked_flow(self):
        require_checker(self)
        proc = check(HANDBACKS / "brief-none.md", HANDBACKS / "complete.md")
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("bad line: Gate flow", out)


if __name__ == "__main__":
    unittest.main()
