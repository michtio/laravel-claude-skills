"""A trusted outside builder runs unattended without a prompt; an untrusted one is skipped (R18, R27).

Decisions log 2026-11-28: "Outside-builder consent is given once per machine: the yes is kept in a trust list
outside the repo, keyed on the exact command, so unattended runs use approved builders". Builder-added test
(G3), beside the S10b gate: the release case `gated-build-trusted` (its own file, since earlier gates lock
evals/behavior-sets/outside-builders.json and outside-builders-confirm.json) runs the fixture non-interactively
with only `./bin/stub-ok` in a throwaway trust file. Expected: the printed list marks stub-ok `(trusted)`, the
other two are `Skipped: <name> (not confirmed)` and never run, stub-ok builds the slice without a question, and
laravel-builder does not start. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_gated_build_trusted.py'
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from outside_builder_support import PROJECT, REPO, SAMPLES, rel  # noqa: E402

CASES = REPO / "evals/behavior-sets/outside-builders-trusted.json"
CASE_ID = "gated-build-trusted"
BAD_REPORTS = {
    "fail-untrusted-ran.md": r"exit",
    "fail-no-trusted-mark.md": r"trusted",
    "fail-built-by-package-builder.md": r"laravel-builder",
    "fail-silent-skip.md": r"stub-fail",
    "fail-asked.md": r"shall",
    "fail-home-trust-file.md": r"\.config",
}


class ReleaseCase(unittest.TestCase):
    """R18, R27: unattended, the trusted builder runs without asking and the others are skipped."""

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
        self.assertEqual(case["expect_agents"], ["laravel-gate-writer", "laravel-review-checker"])
        self.assertEqual(case["forbid_agents"], ["laravel-builder"])
        self.assertLessEqual(case["max_agents"], 5)
        prompt = case["prompt"]
        self.assertIn("laravel-gated-build skill", prompt)
        self.assertIn("non-interactive", prompt)
        self.assertIn("builder_trust.py add", prompt)
        self.assertIn("--name stub-ok", prompt)
        self.assertIn("LARAVEL_CLAUDE_SKILLS_TRUST_FILE", prompt)
        self.assertNotRegex(prompt, r"say yes|I (have read|approve)", "the prompt gives no yes: the trust file does")
        for group in case["must_match"]:
            for pattern in group:
                re.compile(pattern, re.I | re.S)
        for pattern in case["must_not_match"]:
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
