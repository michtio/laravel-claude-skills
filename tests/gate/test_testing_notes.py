"""Testing notes the pack's skills carry: assertions, architecture rules, package suites, concurrency gates,
HTTP tests with several devices, Pest helper scope.

Requirements R1, R5 (test isolation), R6. Gaps rows 33, 42, 60, 108, 130, 135, 144, 153, 155, 156, 167,
168 (the skill half) and 171.
Contract: tests/SkillContent/CONTRACT.md, section "Testing notes".

Every note lives in laravel-pitfalls/references/testing.md (owner ruling: no new skill), which names its
Boost gap and whose `## testing` source section cites each row.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import TESTING, agents, first_line, note  # noqa: E402


class Assertions(unittest.TestCase):
    def test_pii_assertions_name_the_address_not_a_bare_at_sign(self):
        # Row 33
        note(self, r"@anonymous", r"\bbare\b", r"\w+@example\.\w+", row=33,
             label="assert on the specific address, never on a bare @ (an anonymous class name contains @anonymous)")

    def test_a_write_rule_needs_more_than_a_grep(self):
        # Row 42
        note(self, r"save\(", r"increment\(", r"DB::table", row=42,
             label="a writes-only-in-services rule must cover save(), update(), create(), increment() and DB::table writes")
        note(self, r"(query[- ]log|DB::listen)", r"writ", row=42,
             label="or a test runs the code against a query-log listener and asserts where the writes come from")
        note(self, r"grep", r"advisory", row=42,
             label="a grep architecture test is advisory")

    def test_json_test_requests_send_no_cookies(self):
        # Row 153
        note(self, r"(getJson\(\)|postJson\(\)|JSON test)", r"withCredentials\(\)", r"cookie", row=153,
             label="JSON test helpers send no cookies without withCredentials()")

    def test_case_sensitive_fixtures_need_a_binary_collation(self):
        # Row 155
        note(self, r"(utf8mb4_bin|_bin)", r"fixture", r"case-sensitive", row=155,
             label="fixtures for case-sensitive identifiers need a _bin collation on MySQL")


class PackageSuites(unittest.TestCase):
    def test_a_package_suite_registers_its_provider_once(self):
        # Row 60
        note(self, r"getPackageProviders", r"(base TestCase|base test case|whole suite|once)", row=60,
             label="register the provider in the base TestCase's getPackageProviders, once for the suite")
        note(self, r"(provider|register)", r"singleton", r"(two (objects|instances)|false)", row=60,
             label="a probe without the provider registered gives a false 'not a singleton'")

    def test_pest_base_case_declared_twice(self):
        # Row 108
        note(self, r"TestCaseAlreadyInUse", r"uses\(", r"extend\(", row=108,
             label="uses(TestCase) in files plus a folder-level pest()->extend() throws TestCaseAlreadyInUse")

    def test_nested_package_config_is_set_after_the_provider(self):
        # Row 135
        note(self, r"mergeConfigFrom", r"(first level|top level|one level|first-level|top-level)", row=135,
             label="mergeConfigFrom merges only the first level of a package config")
        note(self, r"nested", r"after", r"regist", row=135,
             label="set nested package config after the provider is registered, or set the whole sub-array")

    def test_environment_gated_and_boot_time_checks_in_process(self):
        # Row 156
        note(self, r"\['env'\]", r"production", row=156,
             label="app()['env'] = 'production' makes environment('testing') false for the rest of the test")
        note(self, r"register\(", r"(true|force)", r"boot", row=156,
             label="app()->register(Provider::class, true) runs a fresh provider's boot validation again")

    def test_repeated_impure_calls_are_marked_not_suppressed(self):
        # Row 144: may sit in a skill or in the builder's Larastan guidance
        found = first_line([TESTING, agents.agent_path("laravel-builder")], (r"@phpstan-impure", r"(suppress|ignore)"))
        self.assertIsNotNone(found, "neither testing.md nor the builder says: mark a helper @phpstan-impure for "
                                    "repeated calls whose result changes (cache, locks, clocks), rather than suppressing")


class ConcurrencyGates(unittest.TestCase):
    def test_parallel_processes_in_a_package(self):
        # Row 130
        note(self, r"racer", r"Application::create", row=130,
             label="a racer script boots Testbench's Application::create()")
        note(self, r"(barrier|shared start time|start time)", r"(racer|process)", row=130,
             label="the racers wait for a shared start time")
        note(self, r"(shared store|database cache store|every process)", r"array", row=130,
             label="shared state lives where every process sees it, not the pinned array cache")
        note(self, r"exact", r"counts?", r"sequential", row=130,
             label="exact expected counts, so a sequential run passes only when the rule holds")
        note(self, r"(?-i:RESULT:)", row=130,
             label="each racer prints a RESULT: line the parent requires")


class TimeTravel(unittest.TestCase):
    def test_time_travel_loses_file_session_data(self):
        # Row 171
        note(self, r"travel\(\)", r"mtime", r"file", row=171,
             label="travel() moves Carbon but not file mtimes, so the file session handler reads a travelled session back empty")
        note(self, r"(database driver|database session)", r"travel", row=171,
             label="prefer the database session driver for time-travel tests, or design for it")


class SeveralDevices(unittest.TestCase):
    def test_one_test_simulating_several_devices_resets_between_requests(self):
        # Row 167
        note(self, r"forgetGuards\(\)", r"forgetDrivers\(\)", r"session\.store", r"flushQueuedCookies\(\)", row=167,
             label="before each device's request: forgetGuards(), forgetDrivers(), forgetInstance('session.store'), flushQueuedCookies()")
        note(self, r"CookieValuePrefix", r"(encrypt|decrypt)", row=167,
             label="each device encrypts its own cookies with CookieValuePrefix like prepareCookiesForRequest()")
        note(self, r"(device|browser)", r"(own cookies|cookie jar)", row=167,
             label="each simulated device holds its own cookie jar")


class HelperScope(unittest.TestCase):
    def test_a_single_file_run_loads_no_other_files_helpers(self):
        # Row 168, skill half
        note(self, r"(single[- ]file|one file|vendor/bin/pest tests/)", r"(helper|undefined function)", row=168,
             label="a single-file Pest run loads only that file, so a helper from another file is undefined")
        note(self, r"tests/Support", r"(namespaced|autoload)", r"helper", row=168,
             label="shared helpers are autoloaded namespaced classes under tests/Support")


if __name__ == "__main__":
    unittest.main()
