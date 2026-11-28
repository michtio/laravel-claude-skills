"""The hand-back checker binds the Gate flow line to the brief's `Gate commit:` in both directions.

Requirement R26 (the hand-back's gate flow line is checked before the checker runs). Builder-added test (G3),
beside the S10 gate: the gate proves a locked brief rejects a builder-written flow (flow-downgrade.md); this
proves a brief with `Gate commit: none` rejects a locked flow, which would otherwise make up a gate commit.
A brief with no usable `Gate commit:` is a usage error (exit 2), never a form check against nothing.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_handback_flow_binding.py'
"""
from __future__ import annotations

import sys
import tempfile
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


class BriefMustBindTheFlow(unittest.TestCase):
    """R26: a brief whose `Gate commit:` is missing or neither a sha nor `none` binds nothing, so it is a usage error."""

    def test_a_brief_without_a_usable_gate_commit_is_a_usage_error(self):
        require_checker(self)
        source = (HANDBACKS / "brief.md").read_text(encoding="utf-8")
        cases = {
            "missing": source.replace("Gate commit: 3f2a9c1\n", ""),
            "malformed": source.replace("Gate commit: 3f2a9c1", "Gate commit: main"),
            "empty": source.replace("Gate commit: 3f2a9c1", "Gate commit:"),
            "only fenced": source.replace("Gate commit: 3f2a9c1\n", "```\nGate commit: 3f2a9c1\n```\n"),
        }
        with tempfile.TemporaryDirectory() as raw:
            for label, text in cases.items():
                with self.subTest(case=label):
                    self.assertNotEqual(text, source)
                    brief = Path(raw) / f"{label}.md"
                    brief.write_text(text, encoding="utf-8")
                    proc = check(brief, HANDBACKS / "complete.md")
                    out = proc.stdout + proc.stderr
                    self.assertEqual(proc.returncode, 2, out)
                    self.assertIn("no Gate commit (sha or none) in the brief", out)


if __name__ == "__main__":
    unittest.main()
