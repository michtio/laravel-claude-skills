"""Gate test for slice S7 (laravel-layer): profile schema and docs.

Requirements R23, R24 (docs), the plan's schema-drift risk. Acceptance criteria AC13 to AC15
and AC32 are in tests/Profile/*.php; this file holds the checks that need no PHP. Standard
library only. Run: python3 -m unittest discover -s tests/gate

Contract: tests/Profile/CONTRACT.md. In short:
  - schema/skills-profile.schema.json is byte-identical to the Craft pack's file at
    michtio/craftcms-claude-skills main 48f0c241db45bacb0e9d6668afaeafb6473a7143 with
    the builder name pattern added (ruled 2026-11-28: builders[].name gets
    "pattern": "^[A-Za-z0-9._-]{1,64}$" in both packs; git blob
    4cbce501a9aad3f83f02f4435c9b0d6b9948ca0e, sha256 below);
  - docs/profile.md names the profile path and every key of the schema, the six laravel
    keys with their defaults, and the rules (unknown keys, verdict precedence, rerun).
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCHEMA = REPO / "schema/skills-profile.schema.json"
DOCS = REPO / "docs/profile.md"
CRAFT_BLOB = "4cbce501a9aad3f83f02f4435c9b0d6b9948ca0e"
CRAFT_SHA256 = "39b36ee7899fcae616cfd0c050e31325e3a6d88cc391abbdb32ccdbef8102023"

LARAVEL_KEYS = {
    "runner": "auto",
    "house_style": "true",
    "phpstan_level": "8",
    "monitoring": "none",
    "ci": "false",
}


def property_names(node, found: set) -> None:
    """Every key under a `properties` object, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                found.update(value.keys())
            property_names(value, found)
    elif isinstance(node, list):
        for item in node:
            property_names(item, found)


class Schema(unittest.TestCase):
    def test_schema_is_byte_identical_to_the_craft_pack_pin(self):
        self.assertTrue(SCHEMA.is_file(), "schema/skills-profile.schema.json is missing")
        data = SCHEMA.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.assertEqual(blob, CRAFT_BLOB, "git blob sha differs from the Craft pack's schema")
        self.assertEqual(hashlib.sha256(data).hexdigest(), CRAFT_SHA256)

    def test_schema_parses_and_names_its_dialect(self):
        self.assertTrue(SCHEMA.is_file(), "schema/skills-profile.schema.json is missing")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["required"], ["version"])


class Docs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DOCS.is_file():
            raise AssertionError("docs/profile.md is missing")
        cls.text = DOCS.read_text(encoding="utf-8")

    def test_names_the_profile_path_and_the_command(self):
        self.assertIn(".ai/skills-profile.json", self.text)
        self.assertIn("claude-skills:setup", self.text)
        self.assertIn("--check", self.text)

    def test_documents_every_key_of_the_schema(self):
        found: set = set()
        property_names(json.loads(SCHEMA.read_text(encoding="utf-8")), found)
        self.assertTrue({"version", "managed_by", "gate_tests", "builders", "setup", "verdicts", "craft", "laravel"} <= found)
        missing = sorted(key for key in found if f"`{key}`" not in self.text and f"`{key}." not in self.text and f".{key}`" not in self.text)
        self.assertEqual(missing, [], f"keys of the schema not documented in docs/profile.md: {missing}")

    def test_documents_the_laravel_keys_with_their_defaults(self):
        for key, default in LARAVEL_KEYS.items():
            lines = [line for line in self.text.splitlines() if f"`{key}`" in line or f"`laravel.{key}`" in line]
            self.assertTrue(lines, f"laravel key {key} is not documented")
            self.assertTrue(any(f"`{default}`" in line for line in lines), f"the default of {key} (`{default}`) is not on its line")

    def test_documents_the_values_of_the_enums(self):
        for value in ("auto", "ddev", "host", "sentry", "nightwatch", "none", "locked", "builder-written"):
            self.assertIn(f"`{value}`", self.text)

    def test_states_the_rules(self):
        lowered = self.text.lower()
        for phrase in ("unknown keys", "precedence", "default", "rerun", ".github/workflows/claude-skills-gate.yml", "composer test"):
            self.assertIn(phrase, lowered)
        self.assertRegex(self.text, r"(?is)verdicts?.{0,200}(replace|take precedence)")

    def test_names_no_model_or_vendor_builder(self):
        for term in ("qwen", "mistral", "ollama", "gpt", "gemini"):
            self.assertIsNone(re.search(rf"(?i)(?<![a-z]){term}(?![a-z])", self.text), term)


if __name__ == "__main__":
    unittest.main()
