# Gate contract, slice S9c (laravel-layer): field-test fixes, agent rules

Requirements: R7, R15, R16, R17, R22, R25 (decisions log 2026-11-27: "S9c and S9d", "found defects are fixed, never deferred", "project files on everything"; owner ruling for this slice on learnings). Source: `internal-docs/skills-gaps.md`, rows 1 to 127 plus S11-1 and S8-1 as of this gate (rows 124 to 127 were appended while it was written). Plan: slice S9c in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`.

The gate is written before the builder starts. The builder implements to this contract and never edits `tests/S9c/`, the four files below, or any other file under `tests/`, except through the gate writer. The builder closes the rows in `skills-gaps.md` with the commit that fixed them (this file does not edit it). Everything earlier slices pinned stays: in particular S8's "Pass no `model`" for the checker type (R15), S9b's push, todo, tripwire, merge-commit and Project files rules, and S9b section 6 (the setup writes no `.claude/settings.json`).

Run, from the repo root:

```
python3 -m unittest discover -s tests/gate     # includes test_s9c_*.py; the S9b DDEV test needs ddev and takes minutes
sh scripts/check.sh                            # agent budgets (48 KB, checker 16 KB), caps, tool rules
```

Gate files: `tests/gate/test_s9c_gate_writer.py`, `tests/gate/test_s9c_builder.py`, `tests/gate/test_s9c_review_plan.py`, `tests/gate/test_s9c_owner_rules.py`, and from round 2 `tests/gate/test_s9c_round2.py` (section 9). Standard library only, no DDEV, no network.

## 1. How a rule is checked

As in S9b: each test states what an agent must do and checks that the agent's own file carries it in ONE paragraph or bullet (one line of the file), by the operative words (what, when, what never). A keyword elsewhere in the file does not count. Where a hand-back or report line is named, the test reads the fenced template. The tests reuse `one_line`, `section` and `fenced_blocks` from `test_s9b_agents.py`. The agent files must stay inside the startup budgets `scripts/agent_budget.py` checks (`check.sh`): today the builder is 29.0 KB of 48 KB and the checker 9.8 KB of 16 KB, so the checker gets terse lines.

## 2. Gate writer (`test_s9c_gate_writer.py`)

- **Spec (18).** Never opens, reads or greps `plan.md`; works from the text the brief pastes.
- **Names and values (21, 61).** A structure name may be chosen and goes under Open (S9b); a behavioral value the criteria do not state (a range, a message, an event name string, a status) stops the run as a question. A value the brief delegates is pinned in one constant at the top of the test file and listed on `Values chosen:`.
- **Red for its own reason (19, 43, 44, 63, 87, 71, 20).** Test doubles declared lazily inside functions, never at file level; boot or register calls in the tests that need them, not in a shared `beforeEach`; setup through APIs that exist today, the new API only in its own test; a test green today only when the criterion keeps existing behavior, listed on `Green by design:`; a reach-in guard is tested by subclassing the framework class, with the internals it depends on named in the hand-back; an "is refused" criterion catches around the act and asserts the instance, `->throws()` only when the arrange step cannot throw it; an exact-set pin asserts equality, not containment, with its exclusions in a comment and the hand-back; a scanning (architecture or filesystem) test asserts what it scans exists; tests named so each gate filter matches only its own tests, checked by running each filter.
- **Data and fixtures (45, 46, 62, 88, 122, 47, 111).** Packaging checks use `git ls-files` with a file-system fallback; two distinct classes need two declarations (one `new class` site is one class), named classes at the top of a gate file are prefixed with the slice id; every exemption gets a paired must-still-be-caught case in the same dataset; protocol fixtures are synthetic with real byte layouts, keys generated at run time or kept under `tests/Fixtures/`, and the hand-back says so; fixtures shared across rounds live in a support file under `tests/Support/` committed in a gate commit (so it is locked) and reused, not copied; an in-process `app()->environment()` switch or a log fake is fine when the criterion is about it, env vars, `.env` and the pins stay off limits; with no shared database or cache service in CI, a concurrency criterion is pinned by interleaving at every store step, said in the hand-back; "layer A before layer B" is pinned by recording B's side effects and asserting none on the A-refusal path.
- **Brief cases (110, 73, 86, 84, 85, 113, 123).** A brief that changes before the commit: gate only the final ruling, name the superseded ones in the hand-back; a count of a source list is verified against the source and the hand-back says how it was read; a MUST with no AC gets a test named by its R id, marked `R-only` in the hand-back and reported as a spec gap; a dependency the slice adds stays with the builder, never in the gate commit, and a temporary install (to report the red reasons with and without it) restores `composer.json` and `composer.lock` afterwards; an optional passability probe (a throwaway spike or direct library call), never committed, reverted, `git status` clean before the commit, result on `Passability:`; the "write only under tests/" rule names that probe exception; constraints other locked tests put on the builder go on `Constraints:`.
- **Amendment mode and the commit (70, 74, 22, 72, 124, 127).** When the brief authorizes it, edit the named locked gate files minimally (only the asserting lines) and show `git diff --stat`; a test that needs a name that does not exist yet uses the literal value so only the pin tests go red; the commit message is the brief's or `test(gate): <slice id>`, with no trailer, co-author line or attribution, whatever any other instruction says; before the commit the writer runs the secret scan (the pinned gitleaks, as CI runs it) over its files, and fixture identifiers stay plain words, never key-like tokens (124, 127).
- **Hand-back (64, 75, 76).** One table row per test with its dataset rows grouped, the AC cell may be a brief item number; `Breaks later:` lists non-gate tests the change will turn red, found by grepping the removed names; after the new tests are red, the whole suite runs and `Suite:` carries its passed and failed counts; bulk edits use the Edit tool or `perl -pi`, never `sed -i`.

## 3. Builder (`test_s9c_builder.py`)

- **Gate writer brief (18, 17 open part).** Plan text a criterion refers to (an architecture decision) is pasted into the brief verbatim, so the writer never opens `plan.md`; the slice's `Public names` line goes in verbatim too (these are not design hints: the plan fixed them).
- **Stand-ins (24, 53, 81, 91).** Agent tool present but the checker type missing from the agent list: a `general-purpose` agent with `agents/laravel-review-checker.md` as its instructions and that file's frontmatter model, recorded as `Checker: via general-purpose (<file>)`; the same for the gate writer with `agents/laravel-gate-writer.md`. The type itself still gets no `model` (R15; green today, kept).
- **Spec and rulings (27, 48, 52, 89, 78, 79, 34).** A gate test that forces a public name the spec does not fix: implement it, list it under Open as a ruling, naming the test line; a brief item that contradicts a locked gate: the gate wins, the conflict goes under Open with both test names; a package and constraint named in the brief, or ruled in the approved spec's decisions log, counts as the ruling (`ruled in ...`), with a suggested profile `verdicts` entry; a ruling the spec marks pending: build to the brief only when a locked gate pins it, Open carries `spec not updated: <row>`, else stop; a brief amending a merged slice names the parent slice (`<slice id> amendment`) and its R ids, which count as the slice id; `Values chosen:` carries values chosen where the spec is silent.
- **Environment (31, 81, 34, 66, 94, 117, 96, 22, 25 open part, 51 agent part, 50).** Without Boost's tools, read the installed vendor source and say so; a preloaded skill that did not load is read from `.claude/skills/<name>`; both on an `Environment:` hand-back line, with environment changes made; under zsh no path list or command goes in a variable (literal paths, a function, or a bash script with arrays); a filter with `|` is written `ddev exec "vendor/bin/pest --filter='A|B'"`; commits carry no trailer or attribution unless the brief or the project asks; a setup-owned file that blocks a gate is never hand-edited (change the profile, or take it over through the `.dist` file), and after taking one over the builder runs `claude-skills:setup --yes` and commits the manifest with it; a guard on a framework internal uses reflection with `hasProperty`, falls back to the public API, has a canary test, and never `?? []` on the property.
- **Layers (30).** The Build table gains rows for a service provider (registers and boots under Testbench), config validation (boot fails with the message) and a CI workflow (passes `actionlint` or a dry run), and the package form of artisan commands goes through `testbench`.
- **Fail first and existing tests (49, 92, 80, 114, 123).** Canary, architecture and regression-pin tests may be green first when a named mutation turns them red (`<test>: green (pin) -> red under <mutation>`); in the locked flow, tests for rules beyond the gate may be proved by mutation (`red under mutation`) instead of test-first; an existing test may be migrated to a renamed API when its assertions and dataset keep their strength (`<test>: migrated <old> -> <new>`); after each gate round the builder reruns the mutation proofs of its own earlier tests and fixes any gone vacuous; it reads the gate writer's `Constraints:` line before coding.
- **Revert-to-prove (28, 95, 54, 116, 56, 68, 94, 80, 126).** New files: each rule also proved by mutating its guarding line, in addition to the whole-slice revert; several fixes in one file: one hunk at a time, one line per fix; a mutation that stays green is a weak test (strengthen it) or a redundant line (delete it), said in the hand-back; index-level fixes (untracking, renames) are proved by the gate's red run on the gate commit, not reverted; the red run must show `Tests: N failed`, no output is a broken run; copy, revert and restore run as a bash script with arrays, and `git status` shows the tree changed before the red is read; reverting a migrated test file with the code is expected; per mutation, run the whole slice's test files, or name both the refusing and the accepting test of an allow/deny rule (126).
- **Git and lock check (26, 66, 77, 55, 65 open part, 35, 82 open part).** The Checker gate sizing (`git add -N` of the untracked list) runs in `bash`; one literal lock-check command per gate commit, never a loop or a variable; an exit other than 0 or 1 is a broken check; a superseded gate commit gets `Lock check: <hash>: no own files (superseded by <hash>)` and is never lock-checked; when the brief asks for commits, nothing is staged until commit time, commits use `git commit -- <paths>` after checking `git diff --cached`, and a deletion goes with the file that replaces it; a locked gate file that fails Pint or PHPStan stops the run before the push and the hand-back names the file and the fixers; Pint runs with `--dirty` or the builder's own paths, never bare; after a push, `gh pr checks <n> --watch` green or the red job with its failure line, and a slice that adds a workflow runs it before the hand-back; the hand-back has `CI:` and `Commits:` lines.

## 4. Reviewers, checker, planner (`test_s9c_review_plan.py`)

- **Reviewer (96 to 100).** Rerun with a `|` filter quoted as above; a pest exit other than 0 or 1 is a broken rerun; any installed package's source under `vendor/` is evidence for that package, cited by path and line; a driver-dependent defect (the column type and the query read) may be Important when the report says it was not run and gives the reproduction; the report has `Merge: blocked by <findings> | not blocked`; the R table may say `met on <driver>, not met on <driver>`; a preloaded skill that did not load is read from `.claude/skills/<name>` and its absence named; a package with no register row is reported as `no verdict`; the Security checks gain an Auth flows item (challenge or nonce freshness and single use, replay, session stamp lifetime and binding, remember-me against a fresh login, session fixation, third-party events carrying the full user model, and what the code enforces against what the docs hand the consumer).
- **Deep reviewer (118, 96, 97).** Checker type not in the agent list: general-purpose stand-ins with `agents/laravel-review-checker.md` as instructions, named in the Mode line (the cap and the lens models are unchanged); vendor evidence as above; a new sensitive path: a cache, session or lock store used for single use, rate limits or replay, where the reviewer reads the `add`, `put`, `get` and expiry code of every driver the config can name; the quoted filter and broken-rerun rules.
- **Checker (97).** The vendor evidence rule (the deep reviewer pastes its Evidence rule into every lens brief; the checker's own rule must agree).
- **Planner (17 open part).** The planner fixes the public names (classes, methods, config keys, env vars, constants, event names) a slice's criteria rely on before the gate writer starts, on a `- **Public names:**` line of the slice template.

## 5. Owner rules (`test_s9c_owner_rules.py`)

- **Found defects.** The builder, the reviewer, the deep reviewer, the checker and the debugger each state, in one line, that a found defect is fixed in the slice (a finding, for the read-only ones) or raised with the owner, and never marked later, out of scope or for a follow-up. The builder and the debugger say "fix it, or raise it with the owner". No agent tells itself to leave a found bug for a separate change (green today, kept; the debugger's "leave unrelated cleanup" is about cleanup, and its new defect line must sit beside it).
- **Planner briefs.** The slice template carries `- **Project files:**` and the found-defect rule, and a Rules bullet says every slice carries both.
- **Learnings.** Every agent (all seven) states learnings in two kinds, gaps in the agent or skill rules and stack learnings with evidence, and that the hand-back says `none` when there are none; every hand-back or report carries a `Learnings:` line (in the fenced template for the gate writer, builder, debugger and reviewer; inline in backticks for the planner, checker and deep reviewer). Where learnings are stored is not pinned: the hand-back is the record.
- **Project files (plan S9c).** README Agents section states the found-defect rule and the learnings; CHANGELOG `## [Unreleased]` has an entry naming both.
- **Wording.** No em dashes and US spelling (outside code spans) in the seven agent files, README and CHANGELOG (green today, kept).

## 6. Row map

"S9c" names the test class (file prefix `test_s9c_`); "S9d" rows are listed with no test; "closed" rows were fixed by S9b (or S9) and keep their earlier tests.

| Row | Where |
|---|---|
| 1 | open part (setup warning for Boost under `@testbench`) S9d |
| 2, 3, 6, 7, 8, 9, 11, 13 | closed (S9b) |
| 4 | open part (setup-planned `boost.json` seed) S9d |
| 5 | S9d (runner guideline, tinker under `ddev exec`) |
| 10 | open part (`tests/TestCase.php`) S9d: setup, not in the plan's S9d list by number |
| 12, 14, 15 | S9d |
| 16 | open part: agent side in S9c builder `StandIns`, deep reviewer `test_a_missing_checker_type_gets_general_purpose_stand_ins`. The `.claude/settings.json` part was ruled 2026-11-27: the setup never writes it and prints suggested settings instead, built in S9d |
| 17 | open part: planner `Planner` (both tests), builder `test_the_slices_public_names_go_into_the_gate_writers_brief` |
| 18 | gate writer `ReadingTheSpec`, builder `test_spec_text_a_criterion_refers_to_is_pasted_into_the_brief` |
| 19 | gate writer `test_test_doubles_are_declared_lazily`, `test_boot_calls_sit_in_the_tests_that_need_them` |
| 20 | gate writer `test_scanning_tests_assert_that_what_they_scan_exists`, `test_each_gate_filter_matches_only_its_own_tests` |
| 21 | gate writer `test_a_behavioral_value_the_criteria_do_not_state_stops_the_run` |
| 22 | gate writer `test_the_commit_message_is_the_given_form_with_no_trailer_or_attribution`, builder `test_commits_carry_no_trailer_or_attribution_unless_asked` |
| 23 | closed (S9b) |
| 24 | builder `StandIns` |
| 25 | open part: builder `test_a_setup_owned_file_blocking_a_gate_is_taken_over_never_hand_edited` |
| 26 | builder `test_the_sizing_runs_under_bash` |
| 27 | builder `test_a_gate_test_that_forces_a_public_name_the_spec_does_not_fix` |
| 28 | builder `test_new_files_are_proved_by_mutating_the_guarding_line_as_well` |
| 29 | closed (S9b) |
| 30 | builder `Layers` |
| 31 | builder `test_missing_boost_tools_fall_back_to_the_vendor_source` |
| 32 | open part (setup-printed `boost:update` hint) S9d |
| 33 | S9d (testing note) |
| 34 | builder `test_values_chosen_where_the_spec_is_silent_are_handed_back`, `test_the_hand_back_has_an_environment_line` |
| 35 | builder `test_after_a_push_ci_is_watched` |
| 36 to 42 | S9d |
| 43 | gate writer `test_setup_goes_through_apis_that_exist_today` |
| 44 | gate writer `test_a_green_today_test_only_pins_behavior_the_criterion_keeps`, `test_hand_back_has_a_green_by_design_line` |
| 45 | gate writer `test_packaging_checks_ask_git_what_is_tracked` |
| 46 | gate writer `test_two_distinct_classes_need_two_declarations`, `test_named_classes_at_the_top_of_a_gate_file_carry_the_slice_id` |
| 47 | gate writer `test_an_in_process_environment_switch_or_log_fake_is_allowed_when_the_criterion_is_about_it` |
| 48 | builder `test_a_brief_item_that_contradicts_a_locked_gate` |
| 49 | builder `test_canaries_architecture_tests_and_regression_pins_may_be_green_first_under_a_named_mutation` |
| 50 | builder `test_a_guard_on_a_framework_internal_uses_reflection_and_a_canary` (the pitfall recipe with row 39 is S9d) |
| 51 | builder part: `test_after_taking_a_file_over_the_setup_is_rerun_and_the_manifest_committed`; docs and `--check` part S9d |
| 52 | builder `test_a_package_named_in_the_brief_or_ruled_in_the_spec_counts_as_a_ruling` |
| 53 | the row 24 part: builder `StandIns` (23 and 29 closed in S9b) |
| 54 | builder `test_several_fixes_in_one_file_are_proved_one_hunk_at_a_time` |
| 55 | builder `test_the_commit_recipe_stages_nothing_until_commit_time` |
| 56 | builder `test_index_level_fixes_are_proved_by_the_gates_red_run` |
| 57 to 60 | S9d |
| 61 | gate writer `test_a_delegated_value_is_pinned_in_one_constant_and_reported`, `test_hand_back_has_a_values_chosen_line` |
| 62 | gate writer `test_every_exemption_gets_a_paired_catch_case` |
| 63 | gate writer `test_a_reach_in_guard_is_tested_through_a_subclass_with_the_internals_named`, `test_a_green_today_test_only_pins_behavior_the_criterion_keeps` (Green by design) |
| 64 | gate writer `test_the_table_groups_dataset_rows_per_test` |
| 65 | open part: builder `test_a_locked_gate_file_failing_pint_or_phpstan_stops_before_the_push`, `test_pint_runs_on_own_paths_never_bare_once_gate_files_exist` |
| 66 | builder `test_one_literal_lock_check_command_per_gate_commit`, `test_an_exit_other_than_0_or_1_is_a_broken_check`, `test_never_a_list_or_a_command_in_a_shell_variable` |
| 67 | closed (S9b) |
| 68 | builder `test_the_red_run_must_show_a_failed_count` |
| 69 | closed (S9b) |
| 70 | gate writer `test_an_authorized_amendment_edits_named_locked_gate_files_minimally` |
| 71 | gate writer `test_exact_set_pins_assert_equality_with_listed_exclusions` |
| 72 | as row 22 |
| 73 | gate writer `test_a_count_in_the_brief_is_verified_against_the_source` |
| 74 | gate writer `test_an_amendment_uses_a_literal_value_for_a_name_that_does_not_exist_yet` |
| 75 | gate writer `test_breaks_later_lists_non_gate_tests_the_change_turns_red` |
| 76 | gate writer `test_the_whole_suite_runs_after_the_new_tests_are_red`, `test_bulk_edits_never_use_sed_in_place` |
| 77 | builder `test_a_superseded_gate_commit_gets_a_no_own_files_line` |
| 78 | builder `test_a_brief_ruling_the_spec_marks_pending` |
| 79 | builder `test_an_amendment_to_a_merged_slice_names_its_parent` |
| 80 | builder `test_a_mechanical_migration_of_an_existing_test_to_a_renamed_api`, `test_a_migrated_test_file_is_reverted_with_the_code` |
| 81 | open part: builder `StandIns`, `test_missing_boost_tools_fall_back_to_the_vendor_source`, `test_a_missing_preloaded_skill_is_read_from_its_installed_folder`, `test_the_hand_back_has_an_environment_line` |
| 82 | open part: builder `test_the_hand_back_has_ci_and_commits_lines` |
| 83 | closed (S9b) |
| 84 | gate writer `test_a_new_dependency_stays_with_the_builder_and_may_be_installed_temporarily` |
| 85 | gate writer `test_an_uncommitted_passability_probe_is_allowed_and_reverted`, `test_the_write_only_under_tests_rule_names_the_probe_exception`, `test_hand_back_has_a_passability_line` |
| 86 | gate writer `test_a_must_without_an_acceptance_criterion_gets_an_r_only_test`, `test_hand_back_marks_r_only_tests` |
| 87 | gate writer `test_refusal_criteria_catch_around_the_act` |
| 88 | gate writer `test_protocol_fixtures_are_synthetic_with_real_layouts_and_keys_made_at_run_time` |
| 89 | agent part: builder `test_a_package_named_in_the_brief_or_ruled_in_the_spec_counts_as_a_ruling`; the `laravel/passkeys` register row is S9d (with row 106) |
| 90 | closed (S9b row 23: `test_s9b_agents.py` Builder todo tests already pin the fallback this row asks for) |
| 91 | builder `StandIns` |
| 92 | builder `test_in_the_locked_flow_tests_beyond_the_gate_may_be_proved_by_mutation` |
| 93 | ruled 2026-11-27 (R7 amended: a README never cites tests; a docblock or comment names its test). Round 2: `test_s9c_round2.py` F5 `test_reviewers_and_checker_check_r7` |
| 94 | builder `test_the_revert_runs_as_a_bash_script_and_checks_the_tree_changed`, `test_a_filter_with_a_pipe_quotes_the_whole_container_command` |
| 95 | builder `test_new_files_are_proved_by_mutating_the_guarding_line_as_well` |
| 96 | reviewer and deep reviewer `test_a_rerun_with_a_pipe_in_the_filter_quotes_the_whole_container_command`, `test_a_pest_exit_other_than_0_or_1_is_a_broken_rerun` |
| 97 | reviewer `test_any_installed_vendor_package_is_evidence_for_its_own_behavior`, `test_a_driver_dependent_defect_may_be_important_with_its_reproduction`; deep reviewer and checker `test_any_installed_vendor_package_is_evidence` |
| 98 | reviewer `test_the_report_has_a_merge_line`, `test_the_r_table_can_be_met_on_one_driver_and_not_another` |
| 99 | reviewer `test_a_missing_preloaded_skill_is_read_from_its_installed_folder`, `test_a_package_without_a_register_row_is_reported_as_no_verdict` |
| 100 | reviewer `test_security_checks_cover_auth_flows` |
| 101 to 109 | S9d |
| 110 | gate writer `test_a_superseded_brief_gates_only_the_final_ruling`, `test_a_layer_checked_before_another_is_pinned_by_recording_side_effects` |
| 111 | agent part: gate writer `test_concurrency_without_a_shared_service_uses_deterministic_interleaving`; the pitfall recipe S9d |
| 112 | S9d |
| 113 | gate writer passability tests (row 85) and `test_constraints_from_other_locked_tests_are_handed_back` |
| 114 | builder `test_after_each_gate_round_earlier_own_tests_are_checked_for_vacuity` |
| 115 | S9d |
| 116 | builder `test_a_mutation_that_stays_green_is_a_weak_test_or_a_redundant_line` |
| 117 | builder `test_never_a_list_or_a_command_in_a_shell_variable` |
| 118 | deep reviewer `ReviewerDeep` (a, b, c) |
| 119 to 121 | S9d |
| 122 | gate writer `test_shared_gate_fixtures_go_in_a_locked_support_file` |
| 123 | gate writer `test_constraints_from_other_locked_tests_are_handed_back`, `test_hand_back_has_a_constraints_line`; builder `test_the_gate_writers_constraints_line_is_read_before_coding` |
| 124 | agent part: gate writer `test_the_secret_scan_runs_on_the_gate_files_before_the_commit`; gitleaks in DDEV or failing `composer test` without it is S9d (with row 12) |
| 125 | S9d (pitfall: portable LIKE escape) |
| 126 | builder `test_a_mutation_runs_the_whole_slices_tests_or_both_sides_of_an_allow_deny_rule` |
| 127 | agent part: as row 124; the scan's history versus HEAD scope and a sanctioned route for a historical false positive are setup and docs, S9d |
| S11-1 | neither: release runner, slice S11 |
| S8-1 | closed (S9, 0244ab0) |

`docs/brief-format.md` does not exist (it is S10's), so no brief-format rule is pinned here.

## 7. Red on the base commit, green by design

Run on `763870c` (main after S9b): every new test fails because the rule is missing from the agent file (`no single paragraph or bullet states: ...`, or a missing hand-back line), except three that pass today on purpose: `test_the_type_itself_still_starts_without_a_model` (R15: the checker type keeps no `model`; only the stand-in passes one), `test_no_agent_tells_itself_to_leave_a_found_bug_for_later` and `Wording`. Each keeps a rule the change must not break.

## 8. Open (names and wording this gate pins; the owner may rename before the build)

Hand-back and report lines: gate writer `Values chosen:`, `Green by design:`, `Passability:`, `Constraints:`, `Breaks later:`, `Suite:`, the marker `R-only`; builder `Environment:`, `Values chosen:`, `CI:`, `Commits:`, `Checker: via general-purpose (<file>)`, `Lock check: <hash>: no own files (superseded by <hash>)`, `<test>: green (pin) -> red under <mutation>`, `red under mutation`, `<test>: migrated <old> -> <new>`, `spec not updated: <row>`; reviewer `Merge: blocked by <findings> | not blocked`, `met on <driver>, not met on <driver>`, `` `no verdict` ``; every agent `Learnings:`. Planner template `- **Public names:**` and `- **Project files:**`. Phrases: "gate wins", "ruled in", "parent slice", "one literal command per gate commit", "other than 0 or 1" with "broken", "Auth flows", `tests/Support/`, the quoted filter form `ddev exec "vendor/bin/pest --filter='A|B'"`, `claude-skills:setup --yes` with the manifest.

## 9. Round 2 (PR #12 review findings F1 to F13)

Written on `a30754d` (the builder's S9c commit). Gate file: `tests/gate/test_s9c_round2.py`, plus the amendments below to round 1 files. Same lock rules. Owner rulings used: R7 as amended 2026-11-27 (decisions log), and the 2026-11-27 row 16 ruling.

- **F1, pest exits.** PHPUnit exits 2 when a run has errors (`ShellExitCodeCalculator::EXCEPTION_EXIT = 2`, checked in the installed `vendor/phpunit/phpunit/src/TextUI/ShellExitCodeCalculator.php`, PHPUnit 13.4.7, where `hasErrors()` sets it). The builder, the reviewer and the deep reviewer each state in one line: exit 0 is a pass; exit 1, or exit 2 with a `Tests:` result line, is a fail; no result line, or any other exit, is a broken run. No line ties a pest, PHPUnit, rerun or red-run exit to "other than 0 or 1". The git lock-check rule (0 untouched, 1 changed, 128 an error, any other exit broken) stays as test_s9_round2 needs it.
- **F2, F7, stand-ins.** The checker stand-in's prompt (builder Checker gate, deep reviewer) carries the checker's restriction: never writes or edits, never runs tinker or record-rule, starts no agents. The gate writer stand-in's prompt: writes only under `tests/`, never starts agents. Each names where the file is when the pack is a plugin: `${CLAUDE_PLUGIN_ROOT}/agents/<name>.md` (it resolves in agent Markdown bodies to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; https://code.claude.com/docs/en/plugins-reference, "Environment variables", and https://code.claude.com/docs/en/plugins/loading.md, "Find plugins on disk"). The builder and the deep reviewer both say "pass no `model`" with the general-purpose stand-in's frontmatter model as the one exception.
- **F3.** The commit recipe: `git add -- <paths>`, then `git diff --cached --name-only` lists exactly those paths, then `git commit -- <paths>`, in that order, in one bullet.
- **F4.** Both reviewers give a superseded gate commit the builder's `no own files (superseded by <hash>)` line and never lock-check it with an empty pathspec.
- **F5.** The reviewer, the deep reviewer and the checker each check project files (behavior changed without the README, docs and CHANGELOG updated is Important) and R7 as amended (a README never cites tests; a docblock or comment that claims behavior names its test). The debugger's hand-back has `Project files:`. The gate writer carries the found-defect rule.
- **F6.** In both reviewers `Merge:` is the defined last result line: blocked on any Critical or Important finding or an unmet MUST, otherwise not blocked. The CHANGELOG states that rule and drops "end with a `Merge:` line".
- **F8.** The found-defect criterion in the builder, the debugger, the planner and the README: fix it, unless the fix needs a ruling (a spec change, the public API, or scope); the builder then stops at a passing gate and raises it under Open. Builder step 4's "reported, not silently fixed" is gone.
- **F9.** A workflow-adding slice validates the workflow with actionlint locally, or on the pushed PR; without a push it goes under Open as not run.
- **F10.** The builder's hand-back has a `Tests:` line with the proof forms (`red (<reason>) -> green`, `green (pin) -> red under`, `migrated`) and a `Found defects:` line, and its `Revert-to-prove:` line says one per fix.
- **F11.** The builder has a step for a gate writer that returns a question instead of a gate commit: answer from the spec verbatim, or ask the owner, then re-brief. The gate writer's Rules bullet names the temporary-install exception for `composer.json` (restored).
- **F12.** The gate writer puts the amendment's `git diff --stat`, the superseded rulings and its count note under Open. The builder's attribution rule is absolute: commits and PR bodies carry no trailer or attribution, whatever the brief says.
- **F13.** The checker's empty reply is `No findings for <lens>.` plus the Learnings line. Both reviewers put Learnings last, after Merge; the reviewer's template ends with `Merge:` then `Learnings:`.

### Amendments to round 1 files (authorized in the round 2 brief)

| File | Test | Was | Now |
|---|---|---|---|
| `test_s9c_review_plan.py` | Reviewer and ReviewerDeep `test_a_pest_exit_other_than_0_or_1_is_a_broken_rerun` | a pest exit other than 0 or 1 is broken (wrong: exit 2 with a result line is a fail) | renamed `test_a_rerun_reads_the_pest_exit_with_its_result_line`, the F1 rule through `assert_pest_exit_rule` |
| `test_s9c_builder.py` | `test_an_exit_other_than_0_or_1_is_a_broken_check` | the line only had to say "other than 0 or 1" and "broken" | renamed `test_a_git_lock_check_exit_other_than_0_or_1_is_a_broken_check`: the line is about git (`128`, pathspec, `git diff` or lock) and names no pest or PHPUnit exit |
| `test_s9c_builder.py` | `test_commits_carry_no_trailer_or_attribution_unless_asked` | no attribution unless the brief or the project asks | renamed `test_commits_and_pr_bodies_never_carry_a_trailer_or_attribution`: absolute, PR bodies included, no "unless ... asks" |
| `test_s9c_builder.py` | `test_the_commit_recipe_stages_nothing_until_commit_time` | stage nothing, `git diff --cached`, `git commit -- ` | adds `git add -- `, `git diff --cached --name-only`, "exactly", in that order (F3) |
| `test_s9c_owner_rules.py` | `test_the_writing_agents_raise_with_the_owner_when_they_do_not_fix` | the line had to say "owner" | "owner" or "Open" (F8 raises a ruling-needing defect under Open) |

### Red on `a30754d`

Every round 2 test fails on the missing rule (`no single paragraph or bullet states: ...`, a missing hand-back line, or the old wording still present: `reported, not silently fixed`, `unless the brief or the project asks`, the template ending in `### Suggestions`). None is green by design. A passability probe (rule lines added to copies of the agent files, README and CHANGELOG in the scratchpad, never committed) turned all S9c tests and the earlier agent tests (test_s8*, test_s9*, test_s9b_agents, test_s9b_project_files) green together: 368 tests, OK.

### Open (round 2 names)

`${CLAUDE_PLUGIN_ROOT}/agents/` (or the `.claude/plugins/cache/` path), "one exception" with "pass no `model`", "last result line", the `Tests:` and `Found defects:` hand-back lines, "one per fix" on `Revert-to-prove:`, "re-brief".
