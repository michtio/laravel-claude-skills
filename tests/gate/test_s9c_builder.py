"""Gate test for slice S9c (laravel-layer): the builder's rules from the field test.

Requirements R7, R15, R17, R22, R25. Skills-gaps rows 18 (builder side), 22, 24, 26 to 28, 30, 31,
34, 35, 48 to 56, 66, 68, 77 to 80, 89 (agent part), 91, 92, 94 to 96, 114, 116, 117, 123 (builder
side), 126, and the open parts of rows 17, 25, 65, 81 and 82. Contract: tests/S9c/CONTRACT.md section 3.
Standard library only; no DDEV, no network.

Each test checks that agents/laravel-builder.md carries a rule in ONE paragraph or bullet (one line),
by the operative words, not by a fixed sentence.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402
from test_s9b_agents import fenced_blocks, one_line, section  # noqa: E402


def text() -> str:
    return s8.agent_path("laravel-builder").read_text(encoding="utf-8")


def hand_back(test: unittest.TestCase) -> str:
    blocks = [b for b in fenced_blocks(text()) if "Gate flow:" in b and "Built:" in b]
    if not blocks:
        test.fail("the builder's hand-back template is missing")
    return blocks[0]


def hand_back_line(test: unittest.TestCase, label: str) -> str:
    line = next((l for l in hand_back(test).splitlines() if l.startswith(label)), None)
    if line is None:
        test.fail(f"the hand-back template has no {label} line")
    return line


class GateWriterBrief(unittest.TestCase):
    # Row 18 (builder side)
    def test_spec_text_a_criterion_refers_to_is_pasted_into_the_brief(self):
        line = one_line(self, text(), r"(gate writer|its brief)", r"(paste|verbatim|word for word)", r"(architecture decision|plan\.md|plan text)",
                        label="plan text a criterion refers to is pasted into the gate writer's brief, so the writer never opens plan.md")
        self.assertRegex(line, r"(?i)(instead of|never|not)[^.]{0,80}(open|read|grep)")

    # Row 17 (open part): names the plan fixes go to the gate writer
    def test_the_slices_public_names_go_into_the_gate_writers_brief(self):
        line = one_line(self, text(), r"public names", r"gate writer", r"(slice|plan)",
                        label="the slice's Public names line goes into the gate writer's brief verbatim")
        self.assertRegex(line, r"(?i)(verbatim|as written|copied|paste)")


class StandIns(unittest.TestCase):
    # Rows 24, 91, 53, 81: the agent type is missing but the Agent tool is there
    def test_a_missing_checker_type_gets_a_general_purpose_stand_in_on_the_checkers_model(self):
        line = one_line(self, section(text(), "Checker gate"), r"general-purpose", r"laravel-review-checker\.md",
                        label="checker type missing, Agent tool present: a general-purpose agent with the checker file as its instructions")
        self.assertRegex(line, r"(?i)(missing|not in your agent list|not installed|not listed|no such (agent )?type)")
        self.assertRegex(line, r"(?i)(frontmatter|its own) model")
        self.assertRegex(line, r"Checker: via general-purpose")

    def test_the_hand_back_checker_line_has_the_stand_in_form(self):
        self.assertRegex(hand_back_line(self, "Checker:"), r"via general-purpose")

    def test_a_missing_gate_writer_type_gets_the_same_stand_in(self):
        line = one_line(self, text(), r"general-purpose", r"laravel-gate-writer\.md",
                        label="gate writer type missing, Agent tool present: a general-purpose agent with the gate writer file as its instructions")
        self.assertRegex(line, r"(?i)(frontmatter|its own) model")

    def test_the_type_itself_still_starts_without_a_model(self):
        # R15: the checker type is started without a model override; only the stand-in passes the file's model.
        self.assertRegex(text(), r"Pass no `model`")


class SpecAndRulings(unittest.TestCase):
    # Row 27
    def test_a_gate_test_that_forces_a_public_name_the_spec_does_not_fix(self):
        line = one_line(self, text(), r"public name", r"(spec|plan)[^.]{0,60}(not fix|does not fix|gives no|names no)", r"Open",
                        label="a gate test that forces a public name the spec does not fix: implement it, list it under Open as a ruling, naming the test line")
        self.assertRegex(line, r"(?i)ruling")
        self.assertRegex(line, r"(?i)line")

    # Row 48
    def test_a_brief_item_that_contradicts_a_locked_gate(self):
        line = one_line(self, text(), r"brief", r"(contradict|conflict)", r"gate wins",
                        label="a brief item that contradicts a locked gate: the gate wins, the conflict goes under Open with both test names")
        self.assertRegex(line, r"(?i)Open")
        self.assertRegex(line, r"(?i)test names|both tests")

    # Rows 52, 89 (agent part)
    def test_a_package_named_in_the_brief_or_ruled_in_the_spec_counts_as_a_ruling(self):
        line = one_line(self, text(), r"(named in the brief|the brief names)", r"decisions log", r"ruled in",
                        label="a package and constraint the brief names, or the approved spec's decisions log rules, counts as the ruling")
        self.assertRegex(line, r"(?i)verdicts")

    # Row 78
    def test_a_brief_ruling_the_spec_marks_pending(self):
        line = one_line(self, text(), r"pending", r"locked gate", r"spec not updated",
                        label="a ruling the spec marks pending: build to the brief only when a locked gate pins it, else stop")
        self.assertRegex(line, r"(?i)stop")

    # Row 79
    def test_an_amendment_to_a_merged_slice_names_its_parent(self):
        line = one_line(self, text(), r"amend", r"merged", r"parent slice",
                        label="a brief amending a merged slice names the parent slice and its R ids, and that counts as the slice id")
        self.assertRegex(line, r"(?i)slice id")
        self.assertRegex(line, r"(?i)R ids?")

    # Row 34
    def test_values_chosen_where_the_spec_is_silent_are_handed_back(self):
        one_line(self, text(), r"Values chosen", r"(spec is silent|spec does not state|spec gives no|the spec states none)",
                 label="values the builder chose where the spec is silent go on the Values chosen line")
        hand_back_line(self, "Values chosen:")


class Environment(unittest.TestCase):
    # Rows 31, 81
    def test_missing_boost_tools_fall_back_to_the_vendor_source(self):
        line = one_line(self, text(), r"Boost", r"(absent|missing|not loaded|not available|not in your tool list)", r"vendor",
                        label="without Boost's tools, read the installed vendor source and say so in the hand-back")
        self.assertRegex(line, r"(?i)(hand-back|Environment:)")

    def test_a_missing_preloaded_skill_is_read_from_its_installed_folder(self):
        line = one_line(self, text(), r"preload", r"(missing|absent|not preloaded|not loaded)", r"\.claude/skills",
                        label="a preloaded skill that did not load is read from .claude/skills/<name> and named in the hand-back")
        self.assertRegex(line, r"(?i)(hand-back|Environment:)")

    # Row 34
    def test_the_hand_back_has_an_environment_line(self):
        line = hand_back_line(self, "Environment:")
        self.assertRegex(line, r"(?i)(skill|Boost|tool)")

    # Rows 66, 94, 117: zsh
    def test_never_a_list_or_a_command_in_a_shell_variable(self):
        line = one_line(self, text(), r"zsh", r"variable", r"(function|bash script|script file|array)",
                        label="under zsh a variable is never split: no path list or command in a variable; use literal paths, a function or a bash script with arrays")
        self.assertRegex(line, r"(?i)command")

    # Row 96 (builder side)
    def test_a_filter_with_a_pipe_quotes_the_whole_container_command(self):
        self.assertRegex(text(), r"ddev exec \"vendor/bin/pest --filter='[^'\"]*\|",
                         "a filter with | is written ddev exec \"vendor/bin/pest --filter='A|B'\"")

    # Row 22 (builder side)
    def test_commits_and_pr_bodies_never_carry_a_trailer_or_attribution(self):
        # Amended in round 2 (F12): was "unless the brief or the project asks"; the rule is absolute.
        line = one_line(self, text(), r"commit", r"(trailer|co-author|Co-Authored-By)", r"attribution",
                        label="commits and PR bodies carry no trailer or attribution, whatever the brief says")
        self.assertRegex(line, r"(?i)(whatever|even (if|when))[^.]{0,30}brief")
        self.assertRegex(line, r"(?i)(PR|pull request) (body|bodies|description)")
        self.assertNotRegex(line, r"(?i)(unless|only when)[^.]{0,40}(brief|project) asks")

    # Rows 25 (open part), 51 (builder part)
    def test_a_setup_owned_file_blocking_a_gate_is_taken_over_never_hand_edited(self):
        line = one_line(self, text(), r"setup", r"(owns|owned|claude-skills-setup\.json)", r"(block|fail)",
                        label="a setup-owned config that blocks a gate is never hand-edited: change the profile or take it over")
        self.assertRegex(line, r"(?i)never[^.]{0,60}(hand[- ]edit|edit it|edit the)")
        self.assertRegex(line, r"(?i)(\.dist|take (it )?over|ownership|profile)")

    def test_after_taking_a_file_over_the_setup_is_rerun_and_the_manifest_committed(self):
        line = one_line(self, text(), r"claude-skills:setup --yes", r"(manifest|claude-skills-setup\.json)",
                        label="after taking over a setup-owned file, run claude-skills:setup --yes and commit the manifest")
        self.assertRegex(line, r"(?i)(commit|same change)")

    # Row 50
    def test_a_guard_on_a_framework_internal_uses_reflection_and_a_canary(self):
        line = one_line(self, text(), r"(internal|protected property)", r"hasProperty", r"canary",
                        label="a guard on a framework internal: reflection with hasProperty, fall back to the public API, a canary test, never ?? [] on the property")
        self.assertRegex(line, r"(?i)(public API|fall back|fallback)")
        self.assertIn("?? []", line)


class Layers(unittest.TestCase):
    # Row 30: package layers
    def table_rows(self) -> list:
        return [l for l in section(text(), "Build").splitlines() if l.startswith("|")]

    def row(self, pattern: str, label: str) -> str:
        for l in self.table_rows():
            if re.search(pattern, l.split("|")[1] if l.count("|") > 1 else l, re.I):
                return l
        self.fail(f"the Build table has no row for {label}")

    def test_a_service_provider_row_boots_under_testbench(self):
        self.assertRegex(self.row(r"provider", "a service provider"), r"(?i)testbench")

    def test_a_config_validation_row_fails_boot_with_the_message(self):
        self.assertRegex(self.row(r"config(uration)? validation", "config validation"), r"(?i)(boot|message)")

    def test_a_ci_workflow_row_passes_actionlint(self):
        self.assertRegex(self.row(r"workflow", "a CI workflow"), r"(?i)actionlint")

    def test_package_migrations_use_the_testbench_form(self):
        self.assertRegex(section(text(), "Build"), r"(?i)testbench[^.\n]{0,120}(migrate|artisan)|(migrate|artisan)[^.\n]{0,120}testbench")


class FailFirstAndExistingTests(unittest.TestCase):
    # Row 49
    def test_canaries_architecture_tests_and_regression_pins_may_be_green_first_under_a_named_mutation(self):
        line = one_line(self, text(), r"(canary|architecture|regression pin)", r"mutation", r"green \(pin\) -> red under",
                        label="canary, architecture and regression-pin tests may be green first when a named mutation turns them red")

    # Row 92
    def test_in_the_locked_flow_tests_beyond_the_gate_may_be_proved_by_mutation(self):
        line = one_line(self, text(), r"locked", r"(beyond the gate|the gate does not pin|not pinned by the gate|rules the gate does not)", r"mutation",
                        label="in the locked flow, tests for rules beyond the gate may be proved by a per-fix mutation instead of test-first")
        self.assertRegex(line, r"red under mutation")

    # Row 80
    def test_a_mechanical_migration_of_an_existing_test_to_a_renamed_api(self):
        line = one_line(self, text(), r"renam", r"migrat", r"existing test",
                        label="an existing test may be migrated to a renamed API when its assertions and dataset keep their strength")
        self.assertRegex(line, r"(?i)(strength|assertions)")
        self.assertRegex(line, r"migrated [^\n]{0,30}->")

    # Row 114
    def test_after_each_gate_round_earlier_own_tests_are_checked_for_vacuity(self):
        line = one_line(self, text(), r"(gate round|each round|new round)", r"mutation", r"vacuous",
                        label="after each gate round, rerun the mutation proofs of the builder's own earlier tests; a vacuous one is fixed")
        self.assertRegex(line, r"(?i)(own|earlier)")

    # Row 123 (builder side)
    def test_the_gate_writers_constraints_line_is_read_before_coding(self):
        line = one_line(self, text(), r"Constraints", r"gate writer", r"before",
                        label="the gate writer's Constraints line is read and followed before coding")
        self.assertRegex(line, r"(?i)(cod|build|writ)")


class RevertToProve(unittest.TestCase):
    def rtp(self) -> str:
        return section(text(), "Revert-to-prove")

    # Rows 28, 95
    def test_new_files_are_proved_by_mutating_the_guarding_line_as_well(self):
        line = one_line(self, self.rtp(), r"new (file|class)", r"(mutat|guarding (line|statement))", r"delet",
                        label="for new files, prove each rule by mutating its guarding line, in addition to the whole-slice revert")
        self.assertRegex(line, r"(?i)(in addition|as well|both|besides)")

    # Row 54
    def test_several_fixes_in_one_file_are_proved_one_hunk_at_a_time(self):
        line = one_line(self, self.rtp(), r"(several|more than one|multiple) fix", r"hunk",
                        label="a file holding several fixes: revert one fix's hunk at a time, one Revert-to-prove line per fix")
        self.assertRegex(line, r"(?i)(per fix|each fix|one line)")

    # Row 116
    def test_a_mutation_that_stays_green_is_a_weak_test_or_a_redundant_line(self):
        line = one_line(self, self.rtp(), r"(stays|still) green", r"(redundant|equivalent)",
                        label="a mutation that stays green: a weak test (strengthen it) or a redundant line (delete it), decided by reading")
        self.assertRegex(line, r"(?i)strengthen")
        self.assertRegex(line, r"(?i)(delete|remove)")
        self.assertRegex(line, r"(?i)hand-back")

    # Row 56
    def test_index_level_fixes_are_proved_by_the_gates_red_run(self):
        line = one_line(self, self.rtp(), r"index", r"(untrack|renam|git rm)", r"gate commit",
                        label="index-level fixes (untracking, renames) are proved by the gate's red run on the gate commit, not reverted")
        self.assertRegex(line, r"(?i)(not revert|never revert|no revert|are not reverted)")

    # Row 68
    def test_the_red_run_must_show_a_failed_count(self):
        line = one_line(self, self.rtp(), r"Tests: .{0,6}failed", r"(no output|prints nothing|empty)",
                        label="the red run must show a 'Tests: N failed' line; no output is a broken run, not a proof")
        self.assertRegex(line, r"(?i)broken")

    # Row 94
    def test_the_revert_runs_as_a_bash_script_and_checks_the_tree_changed(self):
        line = one_line(self, self.rtp(), r"bash", r"array", r"git status",
                        label="copy, revert and restore run as a bash script with arrays, and git status shows the revert changed the tree before the red is read")

    # Row 126
    def test_a_mutation_runs_the_whole_slices_tests_or_both_sides_of_an_allow_deny_rule(self):
        line = one_line(self, self.rtp(), r"mutation", r"(accept|allow)", r"(refus|deny)",
                        label="per mutation, run the whole slice's test files, or name both the refusing and the accepting test of an allow/deny rule")
        self.assertRegex(line, r"(?i)(whole slice|all of the slice|every test file of the slice|slice's test files)")

    # Row 80
    def test_a_migrated_test_file_is_reverted_with_the_code(self):
        one_line(self, self.rtp(), r"migrated", r"revert",
                 label="reverting a migrated test file together with the code is expected")


class GitAndLockCheck(unittest.TestCase):
    # Row 26
    def test_the_sizing_runs_under_bash(self):
        one_line(self, section(text(), "Checker gate"), r"git add -N", r"\bbash\b",
                 label="the sizing's untracked list and git add -N run in bash, where the list splits")

    # Row 66
    def test_one_literal_lock_check_command_per_gate_commit(self):
        line = one_line(self, text(), r"(one|a separate) (literal )?command (per|for each) gate commit", r"(loop|variable)",
                        label="one literal lock-check command per gate commit, never a loop or a variable")

    def test_a_git_lock_check_exit_other_than_0_or_1_is_a_broken_check(self):
        # Amended in round 2 (F1): the rule is about git diff --quiet (0, 1, 128), never about a pest exit.
        line = one_line(self, text(), r"(other than 0 or 1|neither 0 nor 1)", r"broken",
                        label="a lock check (git diff --quiet) exit other than 0 or 1 is a broken check, not a verdict")
        self.assertRegex(line, r"(?i)(128|pathspec|git diff|lock)")
        self.assertNotRegex(line, r"(?i)\b(pest|phpunit)\b")

    # Row 77
    def test_a_superseded_gate_commit_gets_a_no_own_files_line(self):
        line = one_line(self, text(), r"supersed", r"no own files",
                        label="a gate commit whose files a later gate commit supersedes: `Lock check: <hash>: no own files (superseded by <hash>)`")
        self.assertRegex(line, r"(?i)never[^.]{0,60}(run|lock-check)")

    # Row 55
    def test_the_commit_recipe_stages_nothing_until_commit_time(self):
        # Amended in round 2 (F3): the recipe is git add -- <paths>, then git diff --cached --name-only lists
        # exactly those paths, then git commit -- <paths>.
        line = one_line(self, text(), r"(stage nothing|nothing is staged|no staging)", r"git commit -- ",
                        label="when the brief asks for commits: stage nothing until commit time; git add -- <paths>, check git diff --cached --name-only lists exactly them, git commit -- <paths>")
        self.assertRegex(line, r"git add -- ")
        self.assertRegex(line, r"git diff --cached --name-only")
        self.assertRegex(line, r"(?i)exactly")
        self.assertLess(line.index("git add -- "), line.index("git diff --cached --name-only"))
        self.assertLess(line.index("git diff --cached --name-only"), line.index("git commit -- "))
        self.assertRegex(line, r"(?i)deletion")

    # Row 65 (open part)
    def test_a_locked_gate_file_failing_pint_or_phpstan_stops_before_the_push(self):
        line = one_line(self, text(), r"gate file", r"(Pint|PHPStan|Larastan)", r"\bstop", r"push",
                        label="a locked gate file that fails Pint or PHPStan stops the run before the push; the hand-back names the file and the fixers")
        self.assertRegex(line, r"(?i)(hand-back|names)")

    def test_pint_runs_on_own_paths_never_bare_once_gate_files_exist(self):
        line = one_line(self, text(), r"pint", r"never[^.]{0,40}bare",
                        label="Pint runs with --dirty or the builder's own paths, never bare once gate files exist")
        self.assertRegex(line, r"(?i)(--dirty|paths|own files|changed files)")

    # Row 35
    def test_after_a_push_ci_is_watched(self):
        line = one_line(self, text(), r"gh pr checks", r"--watch",
                        label="after a push the brief asked for, gh pr checks --watch green, or the red job with its failure line")
        self.assertRegex(line, r"(?i)(red|fail)")
        self.assertRegex(line, r"(?i)workflow")

    # Row 82 (open part)
    def test_the_hand_back_has_ci_and_commits_lines(self):
        hand_back_line(self, "CI:")
        hand_back_line(self, "Commits:")


if __name__ == "__main__":
    unittest.main()
