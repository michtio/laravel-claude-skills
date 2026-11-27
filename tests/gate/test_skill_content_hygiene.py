"""Guards for the new skill content: the pitfall checks stay green, and nothing published names the
field-test projects.

Requirements R1, R2 (AC1, AC3). Green by design: each guards a rule the new content must keep, and
turns red only when the content breaks it.
Contract: tests/SkillContent/CONTRACT.md, section "Hygiene".
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import REPO, SKILLS, read  # noqa: E402

# The field-test projects and their vendor; not on the deny list, but the published pack is fully
# generalized (R2).
FIELD_TEST_NAMES = re.compile(r"auth[ -]?kit|couchgag", re.I)


class PitfallChecks(unittest.TestCase):
    def test_every_pitfall_reference_names_its_boost_gap(self):
        run = subprocess.run([sys.executable, "scripts/check_pitfalls.py"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


class PitfallIndex(unittest.TestCase):
    def test_every_pitfall_reference_is_linked_from_the_skill_index(self):
        refs = sorted((SKILLS / "laravel-pitfalls/references").glob("*.md"))
        self.assertTrue(refs)
        index = read(SKILLS / "laravel-pitfalls/SKILL.md")
        self.assertEqual([r.name for r in refs if f"references/{r.name}" not in index], [],
                         "a pitfall reference is not linked from the laravel-pitfalls index")


class Generalized(unittest.TestCase):
    def test_no_shipped_skill_or_agent_names_a_field_test_project(self):
        paths = sorted(SKILLS.rglob("*.md")) + sorted((REPO / "agents").glob("*.md")) \
            + [REPO / "resources/boost/guidelines/core.blade.php"]
        self.assertTrue(paths)
        hits = [f"{p.relative_to(REPO)}: {m.group(0)}" for p in paths for m in [FIELD_TEST_NAMES.search(read(p))] if m]
        self.assertEqual(hits, [], "published files name a field-test project")


if __name__ == "__main__":
    unittest.main()
