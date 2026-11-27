"""Gate tests for slice S3 (laravel-layer): concurrency, transactions, idempotency.

Requirements R1, R5 (this slice's part), R6, R7. Acceptance criteria AC1, AC6, AC8.
Standard library only. Run: python3 -m unittest discover -s tests/gate

Contracts the builder implements:

* Gap line. A pitfall reference carries one line, at column 0, matching
  `Gap: not covered by Boost` or `Gap: covered partly by Boost (<Boost rule>)`
  with a non-empty rule name in the parentheses.
* Checker: `python3 scripts/check_pitfalls.py [--root DIR]` scans
  `DIR/resources/boost/skills/laravel-pitfalls/references/*.md`. Exit 1 with
  `<file>: no gap line` when the line is missing, and `<file>: names no Boost rule`
  when `covered partly` has no parenthesised rule. Exit 0 otherwise.
* Rule: `Michtio\\LaravelClaudeSkills\\PHPStan\\Rules\\NoSideEffectInTransactionRule`,
  registered in `extension.neon` at the repo root. Its message names
  `laravel-pitfalls: transactions` (see tests/PHPStan/Rules).
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SKILL_DIR = REPO / "resources/boost/skills/laravel-pitfalls"
REFS = ["concurrency", "transactions", "idempotency"]
GAP = re.compile(r"^Gap: (not covered by Boost|covered partly by Boost \(\S.*\))\s*$", re.MULTILINE)
RULE_CLASS = "Michtio\\LaravelClaudeSkills\\PHPStan\\Rules\\NoSideEffectInTransactionRule"


def run(cmd, timeout=900):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)


def ref(name: str) -> str:
    path = SKILL_DIR / "references" / f"{name}.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


class GapLineChecker(unittest.TestCase):
    CHECK = ["python3", "scripts/check_pitfalls.py", "--root"]

    def test_reference_without_gap_line_fails(self):
        r = run(self.CHECK + ["evals/fixtures/pitfall-no-gap"])
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("concurrency.md", out)
        self.assertIn("no gap line", out)

    def test_covered_partly_without_a_rule_fails(self):
        r = run(self.CHECK + ["evals/fixtures/pitfall-partly-no-rule"])
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("names no Boost rule", out)

    def test_valid_reference_passes(self):
        r = run(self.CHECK + ["evals/fixtures/pitfall-valid"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_fixtures_are_what_the_gate_says(self):
        base = REPO / "evals/fixtures"
        sub = "resources/boost/skills/laravel-pitfalls/references/concurrency.md"
        self.assertIsNone(GAP.search((base / "pitfall-no-gap" / sub).read_text()))
        self.assertIsNotNone(GAP.search((base / "pitfall-valid" / sub).read_text()))
        self.assertIsNone(GAP.search((base / "pitfall-partly-no-rule" / sub).read_text()))


class PitfallFacts(unittest.TestCase):
    def test_reference_files_exist(self):
        for name in REFS:
            with self.subTest(ref=name):
                self.assertTrue((SKILL_DIR / "references" / f"{name}.md").is_file())

    def test_each_reference_has_a_gap_line(self):
        for name in REFS:
            with self.subTest(ref=name):
                self.assertRegex(ref(name), GAP)

    def test_skill_index_links_all_three(self):
        index = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for name in REFS:
            with self.subTest(ref=name):
                self.assertIn(f"references/{name}.md", index)

    def test_concurrency_names_lock_and_recheck(self):
        self.assertIn("lockForUpdate", ref("concurrency"))

    def test_transactions_names_after_commit(self):
        self.assertIn("afterCommit", ref("transactions"))

    def test_idempotency_names_unique_key_on_provider_event_id(self):
        text = ref("idempotency")
        self.assertRegex(text, r"(?i)unique")
        self.assertRegex(text, r"(?i)(provider|webhook)[ _-]?event[ _-]?id|event[ _-]id")

    def test_extension_neon_registers_the_rule(self):
        neon = REPO / "extension.neon"
        self.assertTrue(neon.is_file(), "extension.neon missing")
        self.assertIn(RULE_CLASS, neon.read_text(encoding="utf-8"))


class RuleSuite(unittest.TestCase):
    def test_pest_phpstan_filter_is_green(self):
        r = run(["ddev", "exec", "vendor/bin/pest", "--filter=PHPStan"])
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
