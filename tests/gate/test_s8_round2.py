"""Gate test for slice S8, round 2 (laravel-layer): review gaps in the four agents.

Contract: tests/Agents/CONTRACT.md section 5. Standard library only. Each test states a
behaviour a real agent must follow and checks that the agent's text carries it. What a model
does with the text is the release runner's job (slice S11).
"""
from __future__ import annotations

import re
import unittest

import test_s8 as s8

I_S = re.I | re.S
WIPING_TRAITS = ("RefreshDatabase", "DatabaseMigrations", "DatabaseTruncation", "LazilyRefreshDatabase")


def text(test: unittest.TestCase, stem: str) -> str:
    return s8.read_agent(test, stem)


def section(body: str, start: str, end: str) -> str:
    a = body.find(start)
    b = body.find(end, a + 1) if a >= 0 else -1
    return body[a:b] if a >= 0 and b > a else ""


class BuilderGateFlow(unittest.TestCase):
    """Ruling 1 (R22): the opt-out and the isolation check come before a caller-supplied gate commit."""

    def test_caller_commit_is_evaluated_after_opt_out_and_isolation(self):
        body = text(self, "laravel-builder")
        flow = section(body, "**Which flow.**", "**Locked flow.**")
        self.assertTrue(flow, "the 'Which flow' list is missing")
        caller = re.search(r"caller gives a gate commit", flow)
        optout = re.search(r"profile opts out", flow)
        isolated = re.search(r"no isolated suite", flow)
        self.assertTrue(caller and optout and isolated)
        self.assertLess(optout.start(), caller.start(), "the profile opt-out must be decided before the caller's commit")
        self.assertLess(isolated.start(), caller.start(), "isolation must be decided before the caller's commit")

    def test_a_caller_commit_only_means_no_second_gate_writer(self):
        self.assertRegex(text(self, "laravel-builder"),
                         r"(?is)caller gives a gate commit.{0,300}only\b.{0,200}no second gate writer|"
                         r"only means.{0,120}start no second gate writer")

    def test_supplied_commit_on_a_non_isolated_suite(self):
        body = text(self, "laravel-builder")
        self.assertIn("Gate commit (supplied, not locked): <hash>", body)
        self.assertRegex(body, r"(?is)supplied.{0,600}(both lock checks?|lock checks?).{0,200}(run|paste)")
        self.assertIn("suite not isolated: tests ran against the configured DB", body)
        self.assertRegex(body, r"(?is)suite not isolated.{0,200}Open|Open.{0,200}suite not isolated")

    def test_stops_before_the_first_run_on_database_wiping_tests(self):
        body = text(self, "laravel-builder")
        for trait in WIPING_TRAITS:
            self.assertIn(trait, body, f"the wiping trait {trait} is not named")
        self.assertRegex(body, r"(?is)(RefreshDatabase|DatabaseTruncation).{0,500}before the first (test )?run|"
                               r"before the first (test )?run.{0,500}(RefreshDatabase|DatabaseTruncation)")
        self.assertRegex(body, r"(?i)asks? for the pin")
        self.assertRegex(body, r"(?is)stop[^.]{0,200}only[^.]{0,300}(trait|RefreshDatabase)|only[^.]{0,200}(trait|RefreshDatabase)[^.]{0,300}stop")

    def test_isolation_counts_in_memory_sqlite(self):
        body = text(self, "laravel-builder")
        self.assertIn(":memory:", body)
        self.assertRegex(body, r"(?i)testbench")
        self.assertRegex(body, r"(?is)(:memory:|in-memory).{0,300}isolated|isolated.{0,300}(:memory:|in-memory)")


class BuilderTests(unittest.TestCase):
    """Ruling 3 (G4, builder-wide), ruling 6 (revert-to-prove safety)."""

    def test_never_weakens_an_existing_test(self):
        body = text(self, "laravel-builder")
        lines = [l for l in body.splitlines() if re.search(r"(?i)existing tests?", l)]
        ok = [l for l in lines if all(re.search(w, l, re.I) for w in (r"skip", r"todo", r"only", r"delet", r"loosen"))]
        self.assertTrue(ok, "no line says the builder never skips, todos, onlys, deletes or loosens an existing test")
        self.assertRegex(" ".join(ok), r"(?i)never")

    def test_never_edits_test_config_to_get_green(self):
        body = text(self, "laravel-builder")
        lines = [l for l in body.splitlines() if "tests/Pest.php" in l]
        self.assertTrue(any("TestCase" in l and "phpunit.xml" in l and re.search(r"(?i)never", l) for l in lines),
                        "no line forbids editing tests/Pest.php, TestCase and the phpunit.xml pins")
        self.assertRegex(body, r"(?i)report(s|ing)? (a |the )?(red )?(old|existing|earlier) test|red (old|existing) test")

    def test_gate_files_come_from_the_commit(self):
        body = text(self, "laravel-builder")
        self.assertIn("git show --name-only --format= <gate commit>", body)
        self.assertRegex(body, r"(?i)never from (a|the|any) hand-?back")

    # The stash-based revert-to-prove tests of round 2 are replaced by test_s8_round3.py (ruling: no stash, no index).


class BuilderNits(unittest.TestCase):
    def test_explicit_profile_runner_wins_over_detection(self):
        body = text(self, "laravel-builder")
        self.assertRegex(body, r"(?is)(explicit|profile)[^.]{0,80}runner[^.]{0,200}(wins|takes precedence|overrides)[^.]{0,200}(detect|\.ddev)")

    def test_no_ddev_and_no_named_command_asks_or_stops(self):
        self.assertRegex(text(self, "laravel-builder"), r"(?is)no `\.ddev/`[^.]{0,300}\b(ask|stop)")

    def test_missing_register_is_reported_and_means_no_verdict(self):
        pattern = (r"(?is)(missing|not installed|cannot load|not available)[^.]{0,200}register.{0,400}no verdict|"
                   r"register[^.]{0,200}(missing|not installed|cannot load|not available).{0,400}no verdict")
        for stem in ("laravel-builder", "laravel-planner"):
            with self.subTest(agent=stem):
                self.assertRegex(text(self, stem), pattern)
                self.assertRegex(text(self, stem), r"(?is)report[^.]{0,200}(missing|not installed|cannot load)|(missing|not installed|cannot load)[^.]{0,200}report")

    def test_mirrors_the_craft_builder_sections(self):
        body = text(self, "laravel-builder")
        self.assertRegex(body, r"(?is)more than 3 steps.{0,300}(todo list|TodoWrite|TaskCreate)")
        self.assertRegex(body, r"(?is)before[^.]{0,200}(todo list|code)|mandatory")
        self.assertRegex(body, r"(?i)simplification pass")
        self.assertRegex(body, r"(?is)stop early.{0,300}passing gate.{0,300}remainder")
        self.assertRegex(body, r"(?im)^#+ .*manual checks|^\*\*Manual checks")
        self.assertRegex(body, r"(?m)^Reuse: ")


class GateWriter(unittest.TestCase):
    """Rulings 2 and 4 (G2 staging, isolation before the first run) and the empty-filter nit."""

    def test_verifies_the_staged_files_before_committing(self):
        body = text(self, "laravel-gate-writer")
        self.assertIn("git diff --cached --name-only", body)
        self.assertRegex(body, r"(?is)git diff --cached --name-only.{0,500}(equal|exactly|only)[^.]{0,200}(your|its) (own )?(test )?files")
        self.assertRegex(body, r'git commit -m "test\(gate\): <slice id>" -- <')
        self.assertRegex(body, r"(?is)(stop|anything else)[^.]{0,200}staged|staged[^.]{0,200}stop")

    def test_checks_isolation_before_its_first_run(self):
        body = text(self, "laravel-gate-writer")
        self.assertRegex(body, r"(?is)before (your|the) first (test )?run.{0,600}DB_DATABASE|DB_DATABASE.{0,600}before (your|the) first (test )?run")
        self.assertIn('force="true"', body)
        self.assertRegex(body, r"(?i)sqlite")
        self.assertIn(":memory:", body)
        self.assertRegex(body, r"(?is)(missing|no pin|not pinned)[^.]{0,200}stop|stop[^.]{0,200}(missing|no pin|not pinned|not isolated)")

    def test_no_tests_found_is_not_red(self):
        self.assertRegex(text(self, "laravel-gate-writer"),
                         r"(?is)No tests found[^.]{0,250}not[^.]{0,80}right reason")


class ReadOnlyHonesty(unittest.TestCase):
    """Ruling 5: planner and checker."""

    AGENTS = ("laravel-planner", "laravel-review-checker")

    def test_every_nameable_write_tool_is_denied_and_boost_tools_stay_reachable(self):
        for stem in self.AGENTS:
            with self.subTest(agent=stem):
                data = s8.frontmatter(self, stem)
                disallowed = set(s8.agent_budget.as_list(data, "disallowedTools"))
                for tool in ("Write", "Edit", "NotebookEdit", "Agent", s8.TINKER, s8.RECORD_RULE):
                    self.assertIn(tool, disallowed)
                self.assertNotIn("tools", data, "a tools: allowlist would cut off Boost's tools (AD3)")

    def test_bash_is_limited_by_instruction_only_and_the_classes_are_listed(self):
        for stem in self.AGENTS:
            body = text(self, stem)
            with self.subTest(agent=stem):
                self.assertRegex(body, r"(?is)Bash[^.]{0,300}(by instruction|instruction only|only by instruction)|(by instruction|instruction only)[^.]{0,200}Bash")
                for needle in ("migrate", "db:wipe", "composer require", "composer remove", "git commit", "git push", "git stash"):
                    self.assertIn(needle, body, f"{stem} does not list {needle} as forbidden Bash")
                self.assertRegex(body, r"(?i)file writes|writes? (to )?files|redirect")


class CheckerWeakeningList(unittest.TestCase):
    def test_g4_list(self):
        body = text(self, "laravel-review-checker")
        for label, pattern in (("skip", r"->skip\("), ("only", r"->only\("), ("todo markers", r"->todo\("),
                               ("deleted test blocks", r"(?i)delet(ed|ing)[^.\n]{0,30}test blocks?"),
                               ("gate-commit files changed", r"(?i)(changed?|edit(ed|s)?|modif)[^.\n]{0,60}gate[- ]commit|gate[- ]commit[^.\n]{0,60}(files?|changed)"),
                               ("fewer assertions", r"(?i)fewer[^.\n]{0,20}assertions"),
                               ("looser matchers", r"(?i)looser|loosen")):
            with self.subTest(item=label):
                self.assertRegex(body, pattern)


if __name__ == "__main__":
    unittest.main()
