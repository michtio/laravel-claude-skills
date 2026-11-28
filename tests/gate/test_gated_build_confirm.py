"""Gated builds ask before running outside-builder commands (owner ruling 2026-11-28).

Requirements R18 and R27; decisions log 2026-11-28: "Gated builds ask before running outside-builder commands,
as the Craft pack does; an unattended run falls back to the pack's builder". Builder-added test (G3), beside
the S10 gate: the skill and the user docs carry the confirmation rule, the skill runs builders only from the
checked list, and the release case `gated-build-not-confirmed` (its own file, since the S10 gate locks
evals/behavior-sets/outside-builders.json) expects laravel-builder and no stub commit when the user approves
only some commands. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_gated_build_confirm.py'
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from outside_builder_support import (  # noqa: E402
    BUILDERS_DOC, PROFILE_DOC, PROJECT, REPO, SAMPLES, SKILL, assert_line, read_new, rel,
)

CASES = REPO / "evals/behavior-sets/outside-builders-confirm.json"
CASE_ID = "gated-build-not-confirmed"
PRINTED = "<name>: <command> (timeout <n> min)"
SKIPPED = "Skipped: <name> (not confirmed)"
BAD_REPORTS = {
    "fail-stub-ran.md": r"matched forbidden LOG",
    "fail-no-skip-line.md": "not confirmed",
    "fail-built-by-stub.md": "laravel-builder",
    "fail-silent.md": "not confirmed",
}


class ConfirmationRule(unittest.TestCase):
    """R18, R27, ruling 2026-11-28: one line each carries the rule in the skill and both user docs."""

    def test_the_skill_prints_the_list_and_runs_nothing_without_an_exact_yes(self):
        text = read_new(self, SKILL)
        assert_line(self, text, re.escape(PRINTED), r"run none", r"explicit yes",
                    label="print <name>: <command> (timeout <n> min) and run none without an explicit yes")
        assert_line(self, text, r"counts as that yes only when it names every command exactly as the profile has it",
                    label="the request counts only when it names every command exactly")
        assert_line(self, text, r"partial yes", r"non-interactive", r"`laravel-builder`", re.escape(SKIPPED),
                    label="no yes, partial yes or non-interactive: laravel-builder and Skipped: <name> (not confirmed)")
        assert_line(self, text, r"never re-read the profile", label="runs only the commands as printed and confirmed")

    def test_the_user_docs_state_the_same_rule(self):
        for path in (BUILDERS_DOC, PROFILE_DOC):
            with self.subTest(doc=rel(path)):
                text = read_new(self, path)
                assert_line(self, text, re.escape(PRINTED), r"yes", label=f"{rel(path)}: the printed list and the yes")
                assert_line(self, text, r"every command exactly as the profile has it",
                            label=f"{rel(path)}: a request counts only when it names every command exactly")
                assert_line(self, text, r"partial yes", r"`laravel-builder`|package's own builder", re.escape(SKIPPED),
                            label=f"{rel(path)}: partial yes falls back with Skipped: <name> (not confirmed)")


class BuilderValuesNeverReachAShellUnchecked(unittest.TestCase):
    """R18: the skill checks the profile with builders_check.py and runs builders from its file by name."""

    def test_the_skill_uses_the_checked_list_and_the_runner_by_name(self):
        text = read_new(self, SKILL)
        assert_line(self, text, r"builders_check\.py", r"\^\[A-Za-z0-9\._-\]\{1,64\}\$|A-Za-z0-9",
                    label="builders_check.py with the name pattern")
        assert_line(self, text, r"run_builder\.py", r"--builders", r"--name",
                    label="run_builder.py --builders <file> --name <name>")
        self.assertNotIn("--command '<command>'", text)


class ReleaseCase(unittest.TestCase):
    """R27, ruling 2026-11-28: a partial yes runs no stub, and laravel-builder builds the slice."""

    def case(self) -> dict:
        self.assertTrue(CASES.is_file(), f"{rel(CASES)} is missing")
        by_id = {c["id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
        self.assertIn(CASE_ID, by_id)
        return by_id[CASE_ID]

    def test_it_is_well_formed_and_its_facts_hold(self):
        case = self.case()
        self.assertTrue(s8.REQUIRED_KEYS <= set(case), f"missing keys {sorted(s8.REQUIRED_KEYS - set(case))}")
        for key, value in case.items():
            self.assertIn(key, s8.CASE_KEYS, f"unknown key {key}")
            self.assertIsInstance(value, s8.CASE_KEYS[key], key)
        self.assertEqual(s8.fact_failures(case), [])
        self.assertEqual(case["cwd"], rel(PROJECT))
        self.assertTrue(case["copy_cwd"])
        self.assertEqual(case["runs"], 1)
        self.assertEqual(case["expect_agents"], ["laravel-gate-writer", "laravel-builder"])
        self.assertLessEqual(case["max_agents"], 5)
        self.assertIn("laravel-gated-build skill", case["prompt"])
        self.assertIn("say yes to running only `./bin/stub-ok`", case["prompt"])
        self.assertNotIn("`./bin/stub-unavailable`", case["prompt"])
        for group in case["must_match"]:
            for pattern in group:
                re.compile(pattern, re.I | re.S)

    def test_the_good_report_passes_and_each_bad_one_fails_for_its_own_reason(self):
        case = self.case()
        samples = SAMPLES / CASE_ID
        self.assertEqual(s8.score(case, (samples / "pass.md").read_text(encoding="utf-8")), [])
        self.assertEqual({p.name for p in samples.glob("fail-*.md")}, set(BAD_REPORTS))
        for name, needle in BAD_REPORTS.items():
            with self.subTest(sample=name):
                failures = s8.score(case, (samples / name).read_text(encoding="utf-8"))
                self.assertTrue(any(re.search(needle, f) for f in failures), f"{failures} lacks {needle!r}")


if __name__ == "__main__":
    unittest.main()
