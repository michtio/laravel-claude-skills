"""Writing a Laravel package: framework internals, Testbench scripts, package rules and verdict rows.

Requirements R1, R2, R5, R13. Gaps rows 36 (a pitfall reference), 39, 40, 50 (the pitfall recipe), 59, 89 (the register row),
106 (the verdict half) and 132.
Contract: tests/SkillContent/CONTRACT.md, section "Package authoring".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import assert_verdict, files, first_line, pitfall  # noqa: E402


class TaggedServices(unittest.TestCase):
    def test_tagged_services_that_can_fail_to_resolve(self):
        # Row 39
        pitfall(self, 39, r"tagged\(\)", r"(throw|stops at the first)",
                label="Container::tagged() stops at the first abstract that throws")
        pitfall(self, 39, r"registry", r"register\(\)",
                label="instead: a registry the provider fills through an explicit register() method")
        pitfall(self, 39, r"lazy closure",
                label="or wrap each tagged resolution in a lazy closure at tag time")

    def test_a_reach_into_a_framework_internal(self):
        # Rows 50 and 59: the recipe for guarding a framework internal
        pitfall(self, 50, r"(ReflectionClass|hasProperty)", r"fallback", r"canary",
                label="reflection with hasProperty, a fallback to the public API, and a canary test")
        pitfall(self, 50, r"\?\? \[\]", r"(never|silent)",
                label="never `?? []` on the property: that is the silent fallback")
        pitfall(self, 59, r"(shape|unexpected)", r"(public API|null)", r"log(s|ged)? once",
                label="on an unexpected shape fall back to the public API as on a missing property, and log once")


class TestbenchScripts(unittest.TestCase):
    def test_a_testbench_script_that_throws_exits_zero(self):
        # Row 132
        pitfall(self, 132, r"Application::create\(\)", r"exit", r"\b0\b",
                label="a script booting Testbench's Application::create() that throws still exits 0")
        pitfall(self, 132, r"(result marker|RESULT)", r"exit code",
                label="the parent requires a result marker, never only the exit code")


class PackageRules(unittest.TestCase):
    def test_package_author_rules(self):
        # Row 36, as a pitfall reference (the row asks for a package-author reference)
        pitfall(self, 36, r"illuminate/\*", r"require", r"(every|each|all)",
                label="a package declares every illuminate/* component it touches in require")
        pitfall(self, 36, r"composer\.lock", r"(library|package)", r"(never|not|no)\b",
                label="a library does not commit composer.lock")
        pitfall(self, 36, r"\bregister\b", r"\bboot\b", r"provider",
                label="provider register versus boot")
        pitfall(self, 36, r"config", r"\bboot\b", r"(validat|check)",
                label="validate the package config at boot")
        pitfall(self, 36, r"`?final`?", r"providers?",
                label="the package's service providers are final")
        pitfall(self, 36, r"publish", r"tags?",
                label="publishable files carry publish tags")


class Verdicts(unittest.TestCase):
    def test_laravel_passkeys_has_a_verdict(self):
        # Rows 89 and 106: depends (owner ruling), pre-1.0, pin the minor
        assert_verdict(self, "laravel/passkeys", ("depends",), r"pre-1\.0", r"pin(s|ned)? (to )?the minor")

    def test_the_package_author_toolchain_has_verdicts(self):
        # Row 40
        assert_verdict(self, "spatie/laravel-package-tools", ("use", "depends"))
        assert_verdict(self, "orchestra/testbench", ("use", "depends"))
        assert_verdict(self, "larastan/larastan", ("use",))

    def test_illuminate_components_versus_laravel_framework(self):
        # Row 40: the note on what a library requires
        verdict_files = [p for p in files("skills") if "laravel-package-verdicts" in p.parts]
        found = first_line(verdict_files, (r"illuminate/\*", r"laravel/framework", r"require"))
        self.assertIsNotNone(found, "the verdicts skill has no line on illuminate/* versus laravel/framework in require")


if __name__ == "__main__":
    unittest.main()
