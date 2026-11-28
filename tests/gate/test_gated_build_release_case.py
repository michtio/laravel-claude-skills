"""The release case `gated-build-outside`: a gated slice run through the outside builders the fixture profile names.

Acceptance criteria AC26 (gate commit first, the outside builder gets the brief file, the lock check and the
checker run on its result) and AC28 (an outside builder that exits with an error: the build continues with the
next builder named and says so in the report). Requirements R18, R26, R27.
Contract: tests/OutsideBuilders/CONTRACT.md, section "Release case". The case is data for the release runner
(it runs a model); this file proves now that its facts hold against the skill and the docs, that its fixture
is set up as the case says, and that its assertions accept a good report and reject each planted bad one.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_gated_build_release_case.py'
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from outside_builder_support import (  # noqa: E402
    CHECKER, PROJECT, RELEASE_CASES, REPO, SAMPLES, SKILL, read_new, rel,
)

CASE_ID = "gated-build-outside"
STAND_IN_PEST = REPO / "evals/fixtures/builder/isolated-app/vendor/bin/pest"
EXPECTED_BUILDERS = [
    {"name": "stub-unavailable", "command": "./bin/stub-unavailable", "timeout_minutes": 2},
    {"name": "stub-ok", "command": "./bin/stub-ok", "timeout_minutes": 5},
]
# sample -> a substring of the failure it must produce
BAD_REPORTS = {
    "fail-builder-before-gate.md": "LOG",
    "fail-silent-skip.md": "stub-unavailable",
    "fail-handback-rejected.md": r"exit\s*[12]",
    "fail-no-lock-check.md": "Lock check",
    "fail-checker-skipped.md": "skipped|not run",
    "fail-built-by-package-builder.md": "laravel-builder",
    "fail-builder-written-flow.md": "locked",
}


def release_case() -> dict:
    cases = json.loads(RELEASE_CASES.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in cases}
    if CASE_ID not in by_id:
        raise AssertionError(f"{rel(RELEASE_CASES)} has no case {CASE_ID}")
    return by_id[CASE_ID]


class ReleaseCase(unittest.TestCase):
    """AC26, AC28."""

    def test_its_facts_hold_against_the_skill_and_the_docs(self):
        case = release_case()
        self.assertEqual(s8.fact_failures(case), [])
        files = {f["file"] for f in case["facts"]}
        self.assertEqual(files, {rel(SKILL), "docs/outside-builders.md", "docs/brief-format.md"})

    def test_it_covers_both_criteria_and_is_well_formed(self):
        read_new(self, SKILL)
        case = release_case()
        self.assertEqual(case["acs"], ["AC26", "AC28"])
        self.assertTrue(s8.REQUIRED_KEYS <= set(case), f"missing keys {sorted(s8.REQUIRED_KEYS - set(case))}")
        for key, value in case.items():
            self.assertIn(key, s8.CASE_KEYS, f"unknown key {key}")
            self.assertIsInstance(value, s8.CASE_KEYS[key], key)
        self.assertEqual(case["cwd"], rel(PROJECT))
        self.assertTrue(case["copy_cwd"])
        self.assertEqual(case["runs"], 1, "builder cases run once per release")
        self.assertEqual(case["expect_agents"], ["laravel-gate-writer", "laravel-review-checker"])
        self.assertEqual(case["forbid_agents"], ["laravel-builder"])
        self.assertEqual(case["max_agents"], 4)
        for name in case["expect_agents"] + case["forbid_agents"]:
            self.assertTrue(s8.agent_path(name).is_file(), f"{name} has no agent file")
        self.assertIn("laravel-gated-build skill", case["prompt"])
        self.assertIn("`./bin/stub-unavailable` and `./bin/stub-ok`", case["prompt"])
        for group in case["must_match"]:
            for pattern in group:
                re.compile(pattern, re.I | re.S)
        for pattern in case["must_not_match"]:
            re.compile(pattern, re.I | re.S)

    def test_its_fixture_profile_names_the_stubs_in_order_and_reaches_the_checker(self):
        self.assertTrue(CHECKER.is_file(), "scripts/handback_check.py is missing")
        linked = PROJECT / "vendor/michtio/laravel-claude-skills/scripts/handback_check.py"
        self.assertTrue(linked.is_file(), f"{rel(linked)} does not resolve to the package's checker")
        profile = json.loads((PROJECT / ".ai/skills-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["version"], 1)
        self.assertEqual(profile["gate_tests"], "locked")
        self.assertEqual(profile["builders"], EXPECTED_BUILDERS)
        stubs = sorted(p.name for p in (PROJECT / "bin").iterdir())
        self.assertEqual(stubs, ["stub-bad-handback", "stub-ok", "stub-unavailable"])
        for name in stubs:
            mode = (PROJECT / "bin" / name).stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"bin/{name} is not executable")
        pin = s8.env_pins(PROJECT / "phpunit.xml")["DB_DATABASE"]
        self.assertEqual((pin.get("value"), pin.get("force")), ("hello_test", "true"), "the suite is not isolated")
        self.assertEqual((PROJECT / "vendor/bin/pest").read_bytes(), STAND_IN_PEST.read_bytes(),
                         "the stand-in pest differs from the builder fixtures'")
        self.assertEqual(os.path.realpath(PROJECT / ".claude/skills"), os.path.realpath(REPO / "resources/boost/skills"))
        self.assertTrue((PROJECT / ".claude/skills/laravel-gated-build/SKILL.md").is_file(),
                        "the fixture does not see the laravel-gated-build skill")


class ReleaseCaseAssertions(unittest.TestCase):
    """AC26, AC28: the case's assertions accept a good report and reject each planted bad one."""

    def test_the_good_report_passes_and_each_bad_one_fails_for_its_own_reason(self):
        read_new(self, SKILL)
        case = release_case()
        samples = SAMPLES / CASE_ID
        self.assertEqual(s8.score(case, (samples / "pass.md").read_text(encoding="utf-8")), [])
        planted = {p.name for p in samples.glob("fail-*.md")}
        self.assertEqual(planted, set(BAD_REPORTS), "every planted report needs an expected reason")
        for name, needle in BAD_REPORTS.items():
            with self.subTest(sample=name):
                failures = s8.score(case, (samples / name).read_text(encoding="utf-8"))
                self.assertTrue(any(needle in f for f in failures), f"{failures} lacks {needle!r}")


if __name__ == "__main__":
    unittest.main()
