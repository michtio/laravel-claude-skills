"""Gate tests for slice S4 (laravel-layer): authorization, population, PII, edge validation, docs claims.

Requirements R1, R2, R5 (this slice's part), R6, R7. Acceptance criteria AC1, AC3, AC7.
Standard library only. Run: python3 -m unittest discover -s tests/gate

The gap-line checker is covered by test_s3.py. The four rules are proven by their
own must-fail tests in tests/PHPStan/Rules (a no-op rule fails the bad-fixture
test), which the S3 RuleSuite runs through `pest --filter=PHPStan`.

Contracts the builder implements:

* References under resources/boost/skills/laravel-pitfalls/references/:
  authorization.md, population.md, pii-logs.md, edge-validation.md, docs-claims.md.
  Each carries a gap line, SKILL.md links each, and each says which check covers it
  or the words "review only". authorization and population are review only.
  edge-validation names NoUnescapedLikeRule and Larastan's noEnvCallsOutsideOfConfig, and
  says the cast pitfall is review only (owner ruling 2026-11-27, plan AD9);
  pii-logs names NoPayloadInLogRule.
* Rules in Michtio\\LaravelClaudeSkills\\PHPStan\\Rules, registered in extension.neon.
  Messages end "See laravel-pitfalls: edge-validation." (the like rule)
  and "See laravel-pitfalls: pii-logs." (log rule).
* Every published pitfall id has a `## <id>` section in internal-docs/pitfall-sources.md
  (git-ignored; that assertion is skipped when the file is absent, as in CI).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = REPO / "resources/boost/skills/laravel-pitfalls"
REFS = ["authorization", "population", "pii-logs", "edge-validation", "docs-claims"]
REVIEW_ONLY = ["authorization", "population"]
RULES = {
    "edge-validation": ["NoUnescapedLikeRule", "noEnvCallsOutsideOfConfig"],
    "pii-logs": ["NoPayloadInLogRule"],
}
GAP = re.compile(r"^Gap: (not covered by Boost|covered partly by Boost \(\S.*\))\s*$", re.MULTILINE)
NS = "Michtio\\LaravelClaudeSkills\\PHPStan\\Rules\\"


def ref(name: str) -> str:
    path = SKILL_DIR / "references" / f"{name}.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


class PitfallFacts(unittest.TestCase):
    def test_reference_files_exist(self):
        for name in REFS:
            with self.subTest(ref=name):
                self.assertTrue((SKILL_DIR / "references" / f"{name}.md").is_file())

    def test_each_reference_has_a_gap_line(self):
        for name in REFS:
            with self.subTest(ref=name):
                self.assertRegex(ref(name), GAP)

    def test_skill_index_links_all_five(self):
        index = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for name in REFS:
            with self.subTest(ref=name):
                self.assertIn(f"references/{name}.md", index)

    def test_each_reference_names_its_check_or_review_only(self):
        for name in REFS:
            text = ref(name)
            with self.subTest(ref=name):
                if name in RULES:
                    for rule in RULES[name]:
                        self.assertIn(rule, text)
                elif name in REVIEW_ONLY:
                    self.assertRegex(text, r"(?i)review only")
                else:  # docs-claims: a named check or the words review only
                    self.assertRegex(text, r"(?i)review only|scripts/\S+\.py|\b\w+Rule\b")

    def test_review_only_references_name_no_rule(self):
        for name in REVIEW_ONLY:
            with self.subTest(ref=name):
                self.assertNotRegex(ref(name), r"\bNo\w+Rule\b")

    def test_edge_validation_says_the_cast_pitfall_is_review_only(self):
        self.assertRegex(ref("edge-validation"), r"(?i)review only")

    def test_extension_neon_registers_exactly_the_three_rules(self):
        neon = (REPO / "extension.neon").read_text(encoding="utf-8")
        registered = set(re.findall(r"(?m)^\s*-\s*(\S+)\s*$", neon))
        self.assertEqual(
            registered,
            {NS + "NoSideEffectInTransactionRule", NS + "NoUnescapedLikeRule", NS + "NoPayloadInLogRule"},
        )
        for dropped in ("NoEnvOutsideConfigRule", "NoCastOnEnvRule"):
            with self.subTest(rule=dropped):
                self.assertNotIn(dropped, neon)

    def test_every_published_pitfall_has_a_source_entry(self):
        sources = REPO / "internal-docs/pitfall-sources.md"
        if not sources.is_file():
            self.skipTest("internal-docs/pitfall-sources.md is git-ignored and absent (CI)")
        text = sources.read_text(encoding="utf-8")
        for path in sorted((SKILL_DIR / "references").glob("*.md")):
            with self.subTest(ref=path.stem):
                self.assertRegex(text, rf"(?m)^## {re.escape(path.stem)}\b")


if __name__ == "__main__":
    unittest.main()
