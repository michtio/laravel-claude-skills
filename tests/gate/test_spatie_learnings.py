"""Learnings from spatie/guidelines-skills: Artisan command output, method chaining, config placement,
event and listener names, authorization tests for restricted routes, and its verdict row.

Requirements R1, R2, R13, R15 (decisions log 2026-11-27: "Learnings from spatie/guidelines-skills").
The README coexistence and skills.sh sections shipped already and keep their own tests.
Contract: tests/SkillContent/CONTRACT.md, section "Spatie learnings".

Source read: spatie/guidelines-skills 1.1.0 (2026-08-17),
https://github.com/spatie/guidelines-skills/tree/1.1.0/resources/boost/skills
- spatie-laravel-php: "Always provide feedback", "Show progress for loops, summary at end", "Never mix
  single-line and multi-line chaining", "Add service configs to `config/services.php`", "Use `config()`
  helper, avoid `env()` outside config files", "Events: tense-based (`UserRegistering`, `UserRegistered`)",
  "Listeners: action + `Listener` suffix";
- spatie-security: "Add automated authorization tests to verify only authorized users can access
  restricted functionality".
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import CORE, agent, assert_verdict, files, first_line, house_style_block, line_in, pitfall, read  # noqa: E402
from test_s9b_agents import section  # noqa: E402


def first_line_in(text: str, patterns: tuple):
    for line in text.splitlines():
        if all(re.search(p, line, re.I) for p in patterns):
            return line
    return None


class BuilderArtisanOutput(unittest.TestCase):
    def test_an_artisan_command_reports_progress_and_a_summary(self):
        line_in(self, agent(self, "laravel-builder"), r"(Artisan|console) commands?", r"progress", r"summary",
                label="an Artisan command gives feedback: progress inside a loop (before each item) and a summary at the end")


class HouseStyle(unittest.TestCase):
    def test_never_mix_single_line_and_multi_line_chaining(self):
        line_in(self, read(CORE), r"single-line", r"multi-line", r"chain", r"(never|not) mix",
                label="never mix single-line and multi-line method chaining")

    def test_event_and_listener_naming_hints_sit_in_the_house_style_block(self):
        # Owner ruling: conventions, so inside @if ($houseStyle); with house_style false the team's style governs
        line_in(self, house_style_block(read(CORE)), r"\bevents?\b", r"tense", r"\blisteners?\b",
                label="inside the house-style block: events named by tense (UserRegistering, UserRegistered), listeners by the action they take")
        outside = read(CORE).replace(house_style_block(read(CORE)), "")
        self.assertIsNone(first_line_in(outside, (r"\bevents?\b", r"tense", r"\blisteners?\b")),
                          "the naming hint is outside the house-style block")


class ConfigPlacement(unittest.TestCase):
    def test_service_settings_go_in_config_services_and_are_read_through_config(self):
        pitfall(self, None, r"config/services\.php", r"config\(\)",
                label="third-party service settings go in config/services.php and are read through config(), never env(), outside config files",
                source="spatie/guidelines-skills")
        path, _ = first_line(files("pitfalls"), (r"config/services\.php", r"config\(\)"))
        gap = re.search(r"^Gap: covered partly by Boost \((.*)\)\s*$", read(path), re.M)
        self.assertIsNotNone(gap, f"{path.name}: the config pitfall is covered partly (owner ruling)")
        self.assertIn("rules/config", gap.group(1), "the Gap line names Boost's config rule")
        self.assertIn("noEnvCallsOutsideOfConfig", gap.group(1), "the Gap line names Larastan's noEnvCallsOutsideOfConfig")


class ReviewerChecklist(unittest.TestCase):
    def test_every_restricted_route_has_an_authorization_test(self):
        checks = section(agent(self, "laravel-reviewer"), "Checks")
        self.assertTrue(checks, "laravel-reviewer.md has no Checks section")
        line_in(self, checks, r"authori[sz]ation test", r"(every|each) restricted",
                label="Checks: every restricted route or action has an authorization test (a refused user gets 403 or 404)")


class Verdict(unittest.TestCase):
    def test_spatie_guidelines_skills_has_a_verdict_row(self):
        assert_verdict(self, "spatie/guidelines-skills", ("use", "depends"), r"house_style")


if __name__ == "__main__":
    unittest.main()
