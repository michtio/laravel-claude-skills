"""Gate test: outside builder names in the profile schema (laravel-layer R18).

Ruled 2026-11-28 ("S10 review round 1 follow-ups"): a builder name must match
^[A-Za-z0-9._-]{1,64}$ in the profile schema and in the setup's ProfileValidator, in both
packs. The byte pin against the Craft pack's schema is tests/gate/test_s7.py; this file
names the rule itself, so a red pin says what moved. The validator half is
tests/Profile/BuilderNameValidationTest.php. Standard library only.
Run: python3 -m unittest discover -s tests/gate
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCHEMA = REPO / "schema/skills-profile.schema.json"
BUILDER_NAME_PATTERN = "^[A-Za-z0-9._-]{1,64}$"


class BuilderNameInTheSchema(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCHEMA.is_file(), "schema/skills-profile.schema.json is missing")
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_builder_name_carries_the_name_pattern(self):
        name = self.schema["properties"]["builders"]["items"]["properties"]["name"]
        self.assertEqual(name, {"type": "string", "pattern": BUILDER_NAME_PATTERN})

    def test_builder_name_and_command_stay_required(self):
        self.assertEqual(self.schema["properties"]["builders"]["items"]["required"], ["name", "command"])


if __name__ == "__main__":
    unittest.main()
