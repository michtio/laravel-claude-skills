"""Gate test for slice S9c (laravel-layer): the gate writer's rules from the field test.

Requirements R15, R17, R25. Skills-gaps rows 18 to 22, 43 to 47, 61 to 64, 70 to 76, 84 to 88,
110, 111 (agent part), 113, 122, 123, 124 and 127 (agent part) and the open part of row 17 (gate writer side).
Contract: tests/S9c/CONTRACT.md section 2. Standard library only; no DDEV, no network.

Each test states a behavior the gate writer follows and checks that agents/laravel-gate-writer.md
carries it in ONE paragraph or bullet (one line of the file), by the operative words (what to do,
when, what never), not by a fixed sentence. A keyword somewhere in the file does not count.
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
    return s8.agent_path("laravel-gate-writer").read_text(encoding="utf-8")


def hand_back(test: unittest.TestCase) -> str:
    blocks = [b for b in fenced_blocks(text()) if "Gate commit:" in b]
    if not blocks:
        test.fail("the gate writer's hand-back template (a fenced block with Gate commit:) is missing")
    return blocks[0]


class ReadingTheSpec(unittest.TestCase):
    # Row 18: the writer never sees design notes, so it reads no spec file
    def test_reads_no_spec_file_only_the_text_pasted_into_the_brief(self):
        line = one_line(self, text(), r"plan\.md", r"(never|not|no)\b[^.]{0,80}(open|read|grep|search)",
                        label="the gate writer never opens, reads or greps plan.md")
        self.assertRegex(line, r"(?i)brief")
        self.assertRegex(line, r"(?i)(paste|copied|verbatim|word for word|quoted)")


class NamesAndValues(unittest.TestCase):
    # Row 21: names may be chosen and reported; behavioral values stop the run
    def test_a_behavioral_value_the_criteria_do_not_state_stops_the_run(self):
        line = one_line(self, text(), r"\bvalues?\b", r"(range|message|event name|status|string)", r"\b(stop|question|ask)",
                        label="a behavioral value the criteria do not state (a range, a message, an event name) stops the run")
        self.assertRegex(line, r"(?i)\bnames?\b", "the line draws the line between structure names (chosen, reported) and values (stop)")

    # Row 61: a value choice the caller delegates
    def test_a_delegated_value_is_pinned_in_one_constant_and_reported(self):
        line = one_line(self, text(), r"(delegat|leaves the (choice|value)|asks you to (pick|choose))", r"Values chosen",
                        label="a value the brief delegates is pinned and listed under Values chosen")
        self.assertRegex(line, r"(?i)constant")
        self.assertRegex(line, r"(?i)(top of the (test )?file|one constant|a single constant)")

    def test_hand_back_has_a_values_chosen_line(self):
        self.assertRegex(hand_back(self), r"(?m)^Values chosen:")


class RedForItsOwnReason(unittest.TestCase):
    # Row 19: test doubles that implement a missing interface fatal the whole file
    def test_test_doubles_are_declared_lazily(self):
        line = one_line(self, text(), r"(test doubles?|anonymous class|helper class)", r"(lazil|inside (a |the )?(function|factory|closure|test))",
                        label="test doubles are declared lazily, inside functions, never at file level")
        self.assertRegex(line, r"(?i)(file level|whole file|load|fatal)")

    def test_boot_calls_sit_in_the_tests_that_need_them(self):
        line = one_line(self, text(), r"beforeEach", r"(provider|boot|register)",
                        label="a shared beforeEach that boots the missing provider hides each test's own red reason")
        self.assertRegex(line, r"(?i)(red reason|its own|each test)")

    # Row 43: setup through the API that exists today
    def test_setup_goes_through_apis_that_exist_today(self):
        line = one_line(self, text(), r"(set ?up|arrange)", r"(exist(s)? (today|already|now)|existing API)", r"new API",
                        label="a test sets up through existing APIs and uses the new API only in the test about it")
        self.assertRegex(line, r"(?i)only[^.]{0,60}test")

    # Row 44 and 63: green today on purpose
    def test_a_green_today_test_only_pins_behavior_the_criterion_keeps(self):
        line = one_line(self, text(), r"green", r"(today|before the code|on the base|now)", r"Green by design",
                        label="a test green today is allowed only when the criterion keeps existing behavior, listed under Green by design")
        self.assertRegex(line, r"(?i)(keep|kept|unchanged|existing behavio)")

    # Row 63: a guard on a framework internal
    def test_a_reach_in_guard_is_tested_through_a_subclass_with_the_internals_named(self):
        line = one_line(self, text(), r"(reach-in|framework internal|protected (property|internal))", r"subclass",
                        label="a reach-in guard is tested by subclassing the framework class, naming the internals it depends on in the hand-back")
        self.assertRegex(line, r"(?i)hand-back")

    def test_hand_back_has_a_green_by_design_line(self):
        self.assertRegex(hand_back(self), r"(?m)^Green by design:")

    # Row 87: refusals
    def test_refusal_criteria_catch_around_the_act(self):
        line = one_line(self, text(), r"(refus|is refused)", r"(try|catch)", r"->throws\(",
                        label="an 'is refused' criterion catches around the act and asserts the instance; ->throws() only when the arrange step cannot throw it")
        self.assertRegex(line, r"(?i)\bact\b")
        self.assertRegex(line, r"(?i)(arrange|setup|set up)")

    # Row 71: exact-set pins
    def test_exact_set_pins_assert_equality_with_listed_exclusions(self):
        line = one_line(self, text(), r"(exact set|full set|exact-set|set equality)", r"(equal|equality)", r"contain",
                        label="an exact-set pin asserts equality, not containment, and lists its exclusions")
        self.assertRegex(line, r"(?i)exclu")
        self.assertRegex(line, r"(?i)hand-back")

    # Row 20: non-vacuous scans and filters that match only their own tests
    def test_scanning_tests_assert_that_what_they_scan_exists(self):
        line = one_line(self, text(), r"(arch|architecture|file ?system)", r"(vacuous|empty|non-vacu)",
                        label="an architecture or filesystem test asserts the thing it scans exists, so an empty src is not a pass")
        self.assertRegex(line, r"(?i)(exist|has (php )?files|at least one)")

    def test_each_gate_filter_matches_only_its_own_tests(self):
        line = one_line(self, text(), r"filter", r"(only its own|matches only|match(es)? (no|nothing) (else|other)|overlap)",
                        label="name tests so each gate filter matches only its own tests, checked by running each filter")
        self.assertRegex(line, r"(?i)(run|list)")


class DataAndFixtures(unittest.TestCase):
    # Row 45: packaging checks
    def test_packaging_checks_ask_git_what_is_tracked(self):
        line = one_line(self, text(), r"git ls-files", r"(fall back|fallback|falls back)",
                        label="a packaging criterion asks git what is tracked, falling back to the file system")
        self.assertRegex(line, r"(?i)(file system|filesystem|file_exists)")

    # Row 46: one declaration site is one class
    def test_two_distinct_classes_need_two_declarations(self):
        line = one_line(self, text(), r"(new class|anonymous class)", r"\b(same|one)\b[^.]{0,40}(class|declaration|site)",
                        label="two `new class` calls from one site are the same class: two distinct classes need two declarations")
        self.assertRegex(line, r"(?i)two (declarations|classes|sites)")

    def test_named_classes_at_the_top_of_a_gate_file_carry_the_slice_id(self):
        line = one_line(self, text(), r"named (test )?class", r"top of",
                        label="named classes at the top of a gate file are fine, prefixed with the slice id")
        self.assertRegex(line, r"(?i)(prefix|slice id)")

    # Row 62: exemptions get a paired catch case
    def test_every_exemption_gets_a_paired_catch_case(self):
        line = one_line(self, text(), r"(exemption|allowlist|stay allowed)", r"pair",
                        label="every allowlist or exemption criterion gets a paired case the exemption must not swallow")
        self.assertRegex(line, r"(?i)dataset")
        self.assertRegex(line, r"(?i)(caught|catch|refused|swallow)")

    # Row 88: protocol fixtures and key material
    def test_protocol_fixtures_are_synthetic_with_real_layouts_and_keys_made_at_run_time(self):
        line = one_line(self, text(), r"fixtures?", r"synthetic", r"(key material|private key|keys?\b)",
                        label="protocol fixtures: synthetic with real byte layouts, keys generated at run time or kept under tests/Fixtures/")
        self.assertRegex(line, r"(?i)(run time|runtime|tests/Fixtures)")
        self.assertRegex(line, r"(?i)(recorded|device|hand-back)")

    # Row 122: shared gate fixtures
    def test_shared_gate_fixtures_go_in_a_locked_support_file(self):
        line = one_line(self, text(), r"tests/Support", r"(gate commit|lock)",
                        label="fixtures shared across gate rounds go in a support file under tests/Support that the gate commit locks")
        self.assertRegex(line, r"(?i)(cop(y|ies)|reuse|shared|each round)")

    # Row 47: in-process environment switches
    def test_an_in_process_environment_switch_or_log_fake_is_allowed_when_the_criterion_is_about_it(self):
        line = one_line(self, text(), r"(environment\(\)|\['env'\]|in-process)", r"(fake|mock)",
                        label="an in-process app()->environment() switch or a log fake is fine when the criterion is about it")
        self.assertRegex(line, r"(?i)criterion")
        self.assertRegex(line, r"(?i)(env var|exported|\.env|pins?)", "the line keeps env vars, .env and the pins off limits")

    # Row 111 (agent part): concurrency without a shared service
    def test_concurrency_without_a_shared_service_uses_deterministic_interleaving(self):
        line = one_line(self, text(), r"(concurren|parallel|race)", r"interleav",
                        label="with no shared database or cache service in CI, a concurrency criterion is pinned by interleaving at every store step")
        self.assertRegex(line, r"(?i)(CI|shared service|service)")
        self.assertRegex(line, r"(?i)hand-back")

    # Row 110: layer order
    def test_a_layer_checked_before_another_is_pinned_by_recording_side_effects(self):
        line = one_line(self, text(), r"\blayer", r"\bbefore\b", r"(side effects?|record)",
                        label="'layer A is checked before layer B': record B's side effects and assert none on the A-refusal path")
        self.assertRegex(line, r"(?i)(none|\bno\b|zero)")


class BriefCases(unittest.TestCase):
    # Row 110: superseded briefs
    def test_a_superseded_brief_gates_only_the_final_ruling(self):
        line = one_line(self, text(), r"(supersed|changes before)", r"final",
                        label="when the brief changes before the commit, gate only the final ruling and name the superseded ones")
        self.assertRegex(line, r"(?i)hand-back")

    # Row 73: counts
    def test_a_count_in_the_brief_is_verified_against_the_source(self):
        line = one_line(self, text(), r"\bcount", r"source", r"(verif|check)",
                        label="a count of a source list in the brief is verified against the source")
        self.assertRegex(line, r"(?i)hand-back")

    # Row 86: a MUST with no AC
    def test_a_must_without_an_acceptance_criterion_gets_an_r_only_test(self):
        line = one_line(self, text(), r"MUST", r"(no|without)[^.]{0,40}(acceptance criteri|\bAC\b)", r"R-only",
                        label="a MUST with no acceptance criterion gets a test named by its R id, listed as R-only")
        self.assertRegex(line, r"(?i)(spec gap|gap in the spec)")

    def test_hand_back_marks_r_only_tests(self):
        self.assertRegex(hand_back(self), r"R-only")

    # Row 84: a new dependency
    def test_a_new_dependency_stays_with_the_builder_and_may_be_installed_temporarily(self):
        line = one_line(self, text(), r"(dependency|package)", r"temporar", r"composer\.(json|lock)",
                        label="a dependency the slice adds stays with the builder; a temporary install to read the red reasons is restored")
        self.assertRegex(line, r"(?i)(restore|revert|remove)")
        self.assertRegex(line, r"(?i)(both|with and without)")
        self.assertRegex(line, r"(?i)builder")

    # Rows 85, 113: passability
    def test_an_uncommitted_passability_probe_is_allowed_and_reverted(self):
        line = one_line(self, text(), r"passab", r"(spike|throwaway|probe)", r"(revert|git checkout|restore)",
                        label="a throwaway passability probe, never committed, reverted, git status clean before the commit")
        self.assertRegex(line, r"(?i)(never commit|not commit|uncommitted)")
        self.assertRegex(line, r"(?i)git status")

    def test_the_write_only_under_tests_rule_names_the_probe_exception(self):
        line = one_line(self, section(text(), "Rules"), r"only under `?tests/", r"(probe|spike|temporar)",
                        label="the write-only-under-tests rule allows a reverted probe and nothing else outside tests/")
        self.assertRegex(line, r"(?i)(revert|restore)")

    def test_hand_back_has_a_passability_line(self):
        self.assertRegex(hand_back(self), r"(?m)^Passability:")

    # Rows 113, 123: constraints from other locked tests
    def test_constraints_from_other_locked_tests_are_handed_back(self):
        one_line(self, text(), r"Constraints", r"(other )?locked (gate )?tests?", r"builder",
                 label="the hand-back names constraints other locked tests put on where the builder can put code")

    def test_hand_back_has_a_constraints_line(self):
        self.assertRegex(hand_back(self), r"(?m)^Constraints:")


class Amendment(unittest.TestCase):
    # Rows 70, 74: amendment mode
    def test_an_authorized_amendment_edits_named_locked_gate_files_minimally(self):
        line = one_line(self, text(), r"amend", r"authori[sz]", r"(locked|earlier|existing|committed) gate files?",
                        label="amendment mode: when the brief authorizes it, edit the named locked gate files minimally")
        self.assertRegex(line, r"(?i)(only|minimal)")
        self.assertRegex(line, r"git diff --stat")

    def test_an_amendment_uses_a_literal_value_for_a_name_that_does_not_exist_yet(self):
        line = one_line(self, text(), r"amend", r"literal", r"(not exist|does not exist yet|not yet)",
                        label="in an amendment, a test needing a name that does not exist yet uses the literal value, so only the pin tests go red")
        self.assertRegex(line, r"(?i)pin")

    # Rows 124, 127 (agent part): the secret scan before the commit
    def test_the_secret_scan_runs_on_the_gate_files_before_the_commit(self):
        line = one_line(self, text(), r"(gitleaks|secret scan)", r"before[^.]{0,80}commit",
                        label="run the pinned secret scan (gitleaks, as CI runs it) over the gate files before committing")
        self.assertRegex(line, r"(?i)(key-like|plain words|look like (a )?(key|secret|token))", "fixture identifiers stay plain words, never key-like tokens")

    # Rows 22, 72: the commit message
    def test_the_commit_message_is_the_given_form_with_no_trailer_or_attribution(self):
        line = one_line(self, text(), r"commit", r"(trailer|co-author|Co-Authored-By)", r"attribution",
                        label="the commit message is exactly the brief's or `test(gate): <slice id>`, with no trailer or attribution")
        self.assertRegex(line, r"(?i)brief")
        self.assertRegex(line, r"(?i)(wins|whatever|even when|over any|ambient|other instruction)")


class HandBackShape(unittest.TestCase):
    # Row 64: datasets
    def test_the_table_groups_dataset_rows_per_test(self):
        line = one_line(self, text(), r"dataset", r"(one row per test|per test|grouped)",
                        label="the hand-back table may have one row per test with its dataset rows grouped")
        self.assertRegex(line, r"(?i)(brief item|item number)")

    # Row 75: tests outside the gate that the change will break
    def test_breaks_later_lists_non_gate_tests_the_change_turns_red(self):
        line = one_line(self, text(), r"Breaks later", r"(grep|search)",
                        label="Breaks later: non-gate tests the change will turn red, found with a grep for the removed names")
        self.assertRegex(line, r"(?i)(removed|renamed)")
        self.assertRegex(hand_back(self), r"(?m)^Breaks later:")

    # Row 76: the whole suite
    def test_the_whole_suite_runs_after_the_new_tests_are_red(self):
        line = one_line(self, text(), r"(whole|full|entire) suite", r"(passed|failed|counts?)",
                        label="after the new tests are red, run the whole suite and report its passed and failed counts")
        self.assertRegex(line, r"(?i)Suite:")
        self.assertRegex(hand_back(self), r"(?m)^Suite:")

    def test_bulk_edits_never_use_sed_in_place(self):
        line = one_line(self, text(), r"sed -i", r"(never|not|avoid)",
                        label="bulk edits use the Edit tool or perl -pi, never sed -i (BSD and GNU differ)")
        self.assertRegex(line, r"(?i)(perl -pi|Edit tool)")


if __name__ == "__main__":
    unittest.main()
