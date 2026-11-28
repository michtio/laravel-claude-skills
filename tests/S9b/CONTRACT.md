# Gate contract, slice S9b (laravel-layer): field-test fixes

Requirements: R4, R8, R9, R10, R11, R15, R17, R23 (decisions log 2026-11-27: field-test fixes slice). Source: `internal-docs/skills-gaps.md`, 83 rows from a package field test on the pack (rows 74 to 83 were appended while this gate was written; row 83 was added to S9b by the owner). Plan: slice S9b in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`.

The gate is written before the builder starts. The builder implements to this contract and never edits `tests/S9b/`, the S9b files named below, or any other file under `tests/`, except through the gate writer. The builder closes the rows in `skills-gaps.md` (this file does not edit it). Everything the earlier slices pinned stays, except the two amendments in section 10.

Run, from the repo root, through DDEV for PHP:

```
ddev exec vendor/bin/pest --filter=S9b                          # the PHP gate (tests/Profile/S9b*Test.php)
python3 -m unittest discover -s tests/gate                      # includes test_s9b_*.py; the DDEV one needs ddev and takes minutes
sh scripts/check.sh
ddev exec vendor/bin/pest
```

Never run two gate runs at once: `test_s9b_ddev.py` takes the shared lock (`tests/gate/ddev_lock.py`), builds a DDEV project (`lcs-s9b-package` in `fixtures/.s9b-package`) and deletes it afterwards (`ddev delete -Oy`).

## Split

The set is one gate writer session, in three areas, each its own files: setup (`tests/Profile/S9b*Test.php`, `tests/gate/test_s9b_ddev.py`, fixture `tests/Fixtures/s9b-package/`), README and docs (`tests/gate/test_s9b_docs.py`), agents (`tests/gate/test_s9b_agents.py`). The builder may build them in that order or as three slices of the plan's one slice.

## Row map

Every row of `internal-docs/skills-gaps.md`, with the test that closes it or the reason it is out of scope. "Out of scope" means not in S9b's layers (setup, README, agents as the plan lists them); none was decided by this file: each needs an owner ruling on a slice. In scope: 22 rows (20 from the first 73, plus rows 82 and 83), plus rows 53 and 81 covered through 23 and 29. Out of scope: 59 rows.

| Row | Test or reason |
|---|---|
| 1 | in scope (README part): `test_s9b_docs.py` Readme `test_app_section_runs_setup_then_boost_install_then_setup_again`, `test_package_section_runs_the_same_order_through_testbench`, `test_the_order_says_why_boost_install_runs_between_two_setups`. The setup warning (Boost output under the `@testbench` skeleton, `boost.json` missing) is out of scope: not in S9b's setup layer. |
| 2 | in scope: `test_s9b_docs.py` Readme `test_requiring_the_unreleased_pack_from_vcs` |
| 3 | in scope: `S9bClaudeMdTest.php` (all 9), `test_s9b_docs.py` Readme `test_claude_md_before_boost_is_explained`, `test_s9b_ddev.py` test_1 sub-test "CLAUDE.md exists before Boost" |
| 4 | in scope (README part): `test_s9b_docs.py` Readme `test_non_interactive_boost_recipe`. A setup-planned `boost.json` seed is not pinned: the plan lists the README recipe only. |
| 5 | out of scope: runner guideline wording (tinker through `ddev exec`) is not in S9b's layers. Needs an owner ruling on a slice. |
| 6 | in scope: `S9bTestDatabaseTest.php` (all), `test_s9b_ddev.py` `FreshPackageOnMysql` test_1 to test_5, `MatrixWorkflowPassesActionlint` |
| 7 | in scope (value and `env`): `S9bTestPinsTest.php` (all), `S9bTestPinsPassThroughTest.php` (all), `test_s9b_ddev.py` test_6, `test_s9b_docs.py` ProfileDocs `test_test_pins_documents_the_env_value` |
| 8 | in scope: `S9bPhpMatrixTest.php` (all), `test_s9b_ddev.py` test_1 sub-test "matrix workflow", `MatrixWorkflowPassesActionlint` |
| 9 | in scope: `S9bPackageSkeletonTest.php` paths tests, `test_s9b_ddev.py` test_1 sub-test "phpstan paths" and test_4 (`composer test` green on an empty `src`) |
| 10 | in scope: `S9bPackageSkeletonTest.php` Pest.php tests, `test_s9b_ddev.py` test_1 and test_4. `tests/TestCase.php` is not required: `Pest.php` extends Testbench's case directly (no autoload-dev edit). |
| 11 | in scope: `test_s9b_docs.py` Readme `test_package_section_creates_the_workbench_and_formats_it` |
| 12 | out of scope: gitleaks in the DDEV container is not in S9b's layers. |
| 13 | in scope: `S9bOutputTest.php` (options with source, `N changes planned`), `test_s9b_docs.py` ProfileDocs `test_ddev_check_exit_line_is_explained`, `test_planned_wording` |
| 14 | out of scope: `testbench.yaml` text-preserving edit is not in S9b's layers. |
| 15 | out of scope: package runner guideline and `enforce_tests` are not in S9b's layers. |
| 16 | in scope: `S9bOutputTest.php` agent-install tests (6), `test_s9b_docs.py` Readme `test_plugin_install_commands`, `test_the_agents_section_points_to_the_install_step_for_the_agents`, `test_s9b_ddev.py` test_1 |
| 17 | in scope (gate writer): `test_s9b_agents.py` GateWriter `test_every_public_name_it_chose_goes_under_open`, `test_the_open_line_of_the_hand_back_carries_the_names`. The planner fixing names before the gate writer is not pinned. |
| 18 | out of scope: how the writer reads a spec without the notes is not in S9b's agent list. |
| 19 | out of scope: lazy test doubles and per-test red reasons are not in S9b's agent list. |
| 20 | out of scope: non-vacuous architecture tests and filter naming are not in S9b's agent list. |
| 21 | out of scope: structure names versus behavioral values is not in S9b's agent list. Row 17's names rule is the only part S9b closes. |
| 22 | out of scope: the commit message form and the no-trailer rule are not in S9b's agent list (the agent files carry no trailer rule today). Cheap candidate for a follow-up. |
| 23 | in scope: `test_s9b_agents.py` Builder `test_without_a_todo_tool_the_steps_go_in_the_first_message_and_the_hand_back`, `test_the_hand_back_has_a_todo_line`, `test_skipping_the_todo_list_silently_is_not_allowed` |
| 24 | out of scope: checker type missing and the `model` argument are not in S9b's agent list. |
| 25 | in scope (paths part): `S9bPackageSkeletonTest.php` `adds workbench/app when it exists`, `lists src and tests`. The builder telling which file to change when a setup-owned config blocks a gate is out of scope. |
| 26 | out of scope: the sizing recipe is not in S9b's agent list. |
| 27 | out of scope: forced public names in the builder's point 4 is not in S9b's agent list. |
| 28 | out of scope: revert-to-prove for new files is not in S9b's agent list. |
| 29 | in scope: `test_s9b_agents.py` Builder `test_push_and_pr_follow_the_brief_on_the_slice_branch_never_main`, `test_without_the_brief_asking_the_builder_does_not_push`, `test_the_hand_back_has_a_pr_line` |
| 30 | out of scope: package layer rows are not in S9b's agent list. |
| 31 | out of scope: Boost tool fallback is not in S9b's agent list. |
| 32 | in scope (README part): `test_s9b_docs.py` Readme `test_boost_update_after_a_ddev_php_change`. A setup-printed hint is not pinned. |
| 33 | out of scope: testing note on `@anonymous` is skill content, not in S9b's layers. |
| 34 | out of scope: `Environment:` and `Values chosen:` hand-back lines are not in S9b's agent list. |
| 35 | out of scope: watching CI after a push is not in S9b's agent list. |
| 36 | out of scope: skill and pitfall content (best-practices, pitfalls, verdicts register). No slice covers it; needs an owner ruling. |
| 37 | out of scope: skill and pitfall content (best-practices, pitfalls, verdicts register). No slice covers it; needs an owner ruling. |
| 38 | out of scope: skill and pitfall content (best-practices, pitfalls, verdicts register). No slice covers it; needs an owner ruling. |
| 39 | out of scope: skill and pitfall content (best-practices, pitfalls, verdicts register). No slice covers it; needs an owner ruling. |
| 40 | out of scope: skill and pitfall content (best-practices, pitfalls, verdicts register). No slice covers it; needs an owner ruling. |
| 41 | out of scope: docs/profile.md PHPStan ownership wording is not in S9b's layers. |
| 42 | out of scope: testing skill content (architecture write rules). |
| 43 | out of scope: gate writer method details are not in S9b's agent list. |
| 44 | out of scope: gate writer method details are not in S9b's agent list. |
| 45 | out of scope: gate writer method details are not in S9b's agent list. |
| 46 | out of scope: gate writer method details are not in S9b's agent list. |
| 47 | out of scope: gate writer method details are not in S9b's agent list. |
| 48 | out of scope: builder gate-test and fail-first details are not in S9b's agent list (50 is pitfall content). |
| 49 | out of scope: builder gate-test and fail-first details are not in S9b's agent list (50 is pitfall content). |
| 50 | out of scope: builder gate-test and fail-first details are not in S9b's agent list (50 is pitfall content). |
| 51 | out of scope: `--check` with a deleted setup-owned file, and its docs, are not in S9b's layers. |
| 52 | out of scope: a brief naming a package counts as a ruling, not in S9b's agent list. |
| 53 | covered through rows 23 and 29 (their tests); row 24 stays out of scope |
| 54 | out of scope: builder revert-to-prove and commit recipe details are not in S9b's agent list. |
| 55 | out of scope: builder revert-to-prove and commit recipe details are not in S9b's agent list. |
| 56 | out of scope: builder revert-to-prove and commit recipe details are not in S9b's agent list. |
| 57 | out of scope: pitfall content (pii-logs, container reach-in). |
| 58 | out of scope: pitfall content (pii-logs, container reach-in). |
| 59 | out of scope: pitfall content (pii-logs, container reach-in). |
| 60 | out of scope: testing note for package providers is skill content. |
| 61 | out of scope: gate writer method details are not in S9b's agent list. |
| 62 | out of scope: gate writer method details are not in S9b's agent list. |
| 63 | out of scope: gate writer method details are not in S9b's agent list. |
| 64 | out of scope: gate writer method details are not in S9b's agent list. |
| 65 | in scope (gate writer side): `test_s9b_agents.py` GateWriter `test_formats_only_its_own_test_files_before_the_commit_and_reruns`, `test_never_formats_the_whole_project_or_a_locked_file`, `test_hand_back_reports_the_format_check_next_to_the_commit`. The builder's stop rule for a locked file failing Pint is out of scope. |
| 66 | out of scope: lock-check loops in zsh are not in S9b's agent list. |
| 67 | in scope: `test_s9b_agents.py` Builder `test_a_tripwire_check_stops_after_one_row_per_bypass_and_documents_the_rest`, `test_tripwire_rounds_count_against_the_briefs_cap`, `test_a_tripwire_is_recognised_by_what_it_is` |
| 68 | out of scope: empty filter in revert-to-prove is not in S9b's agent list. |
| 69 | in scope: same tests as row 65 (gate writer formatting) |
| 70 | out of scope: amendment mode is not in S9b's agent list. |
| 71 | out of scope: exact-set pins are not in S9b's agent list. |
| 72 | out of scope: same as row 22. |
| 73 | out of scope: counting a source list is not in S9b's agent list. |
| 74 | out of scope: amendment mode is not in S9b's agent list. |
| 75 | out of scope: a `Breaks later` hand-back line is not in S9b's agent list. |
| 76 | out of scope: suite result in the gate writer's hand-back is not in S9b's agent list. |
| 77 | out of scope: superseded gate commits in the lock check are not in S9b's agent list. |
| 78 | out of scope: a brief ruling the spec marks pending is not in S9b's agent list. |
| 79 | out of scope: amendments to a merged slice are not in S9b's agent list. |
| 80 | out of scope: migrating an existing test to a renamed API is not in S9b's agent list. |
| 81 | covered through rows 23 and 29 (their tests); the missing checker type and Boost tools stay out of scope (row 24) |
| 82 | in scope (PR line only): `test_s9b_agents.py` Builder `test_the_hand_back_has_a_pr_line`. The `CI:` and `Commits:` lines are not pinned. |
| 83 | in scope: `test_s9b_project_files.py` (all 19 tests): guideline, builder step and `Project files:` line, checker item, the pack's CHANGELOG.md, US spelling and no em dashes |

The merge rule (every gated PR merges with a merge commit, never a squash) has no row: `test_s9b_agents.py` Builder `test_a_gated_pr_merges_with_a_merge_commit_never_a_squash`, `test_the_hand_back_pr_line_names_the_merge_method`, and `test_s9b_docs.py` Readme `test_gated_prs_merge_with_a_merge_commit`.

## 1. `laravel.test_database` (row 6)

- Values: `auto` (the default; today's behavior) and `ddev`. Anything else, including a non-string, is refused as `Invalid profile .ai/skills-profile.json: laravel.test_database: <reason>`, exit 1, nothing written.
- `Profile::laravel()` keeps its five S7 keys, in order, unless the profile sets a new key: then the new key is appended (order `test_database`, `php_matrix`, `test_pins`). The S7 tests pin the five-key array, and this keeps them green.
- `ddev` on a Testbench package that runs on DDEV: the package gets what an app on DDEV gets.
  - `.ddev/config.claude-skills.yaml` holds the post-start hook (service `db`, idempotent, never `exec-host`) for `<slug>_test` (mysql, mariadb or the psql form for postgres), and a `web_environment` list with `DB_HOST=db`, `DB_PORT=<3306 or 5432>`, `DB_USERNAME=db`, `DB_PASSWORD=db` (DDEV's defaults). Host, port and credentials are not forced in `phpunit.xml.dist`: CI sets its own in the job.
  - The pins are `DB_CONNECTION` (from the DDEV database type in `.ddev/config.yaml`: mysql to `mysql`, mariadb to `mariadb`, postgres to `pgsql`; with no `database` block, what the installed DDEV reports: round 4), `DB_DATABASE=<slug>_test` and `DB_URL=""`, each a forced `<env>` and a `<server>` twin. The other pins and the live flags are as before.
  - The CI workflow (`ci: true`) gets the database service and the job environment (`DB_HOST: 127.0.0.1`, port, user, password) as for an app, the database name quoted.
- For an app on DDEV, `ddev` changes nothing (the plan equals the one `auto` gives).
- `ddev` on a project that does not run on DDEV (no `.ddev/`, or `runner: host`): exit 1, a message holding `laravel.test_database` and `DDEV`, nothing written, with `--check` and `--yes` alike. Resolved here: the key is a statement about DDEV, so a mismatch is an error, not a silent fallback.
- Without the key (or `auto`) a package keeps the S6 behavior: no hook, in-memory sqlite pins.
- Changing the key plans only the difference (hook, phpunit file, workflow, state), never "edited by hand", and a rerun says `No changes`.

## 2. `laravel.test_pins` (row 7)

- An object of `NAME: value`. Names: `SESSION_DRIVER`, `CACHE_STORE`, `QUEUE_CONNECTION`, `MAIL_MAILER`. Values: non-empty strings of letters, digits, `_`, `.`, `-`. Anything else is refused as `laravel.test_pins` (not an object) or `laravel.test_pins.<NAME>` (a name that is not allowed, which includes `APP_ENV`, `DB_*`, live flags, lowercase names, and a value that is not allowed), exit 1, nothing written.
- A named pin is written `<env name="<NAME>" value="<value>" force="true"/>`, and its `<server>` twin (`QUEUE_CONNECTION`, `MAIL_MAILER`) carries the same value. Every other pin is written exactly as without `test_pins`. Isolation stays the default.
- Rerun: `No changes`. A changed value plans only that line (not "edited by hand"). Removing the key goes back to the standard value. A hand edit of a pin the profile does not name is still reported.
- Round 1b (owner ruling): each allowed name takes either a value or the literal `env`. `env` writes the pin without force, `<env name="<NAME>" value="<default>"/>` with the standard value as the default (`array`, `array`, `sync`, `array` for `SESSION_DRIVER`, `CACHE_STORE`, `QUEUE_CONNECTION`, `MAIL_MAILER`), and no `<server>` twin (it would beat the shell). A value the shell or `ddev exec env NAME=value` sets then wins; when nothing is set the default applies. Every other pin stays forced. The DB, `APP_ENV` and live-flag pins cannot be named, `env` or not. An unknown name or value is exit 1 as above, nothing written. Rerun, value-to-`env` changes, removal and hand-edit detection (a hand-forced `env` pin is reported) follow the same rules as a value pin. `Profile::load()->laravel()['test_pins']` returns `env` as written. The printed option is `NAME=env`. Pest: `S9bTestPinsPassThroughTest.php`; real run: `test_s9b_ddev.py` test_6, with the fixture profile `test_pins: {"SESSION_DRIVER": "env", "QUEUE_CONNECTION": "env"}` and `tests/Fixtures/s9b-package/tests/SessionDriverTest.php`, run as `ddev exec env SESSION_DRIVER=file QUEUE_CONNECTION=database S9B_EXPECT_SESSION=file S9B_EXPECT_QUEUE=database vendor/bin/pest --filter=SessionDriver` (sees `file` and `database`) and without the variables (sees `array` and `sync`). Finding: on the base commit a forced `SESSION_DRIVER` already lets a shell value through (it has no `<server>` twin; Laravel reads the shell value first), so that check alone is red only on its unforced element; `QUEUE_CONNECTION` (forced plus twin) is red on the value itself.

## 3. `laravel.php_matrix` (row 8)

- Values: `auto` (the default) or a non-empty list of unique `X.Y` strings (`"8.3"`). Otherwise refused as `laravel.php_matrix` or `laravel.php_matrix.<index>`.
- A list, for an app or a package: the workflow job gets `strategy: {fail-fast: false, matrix: {php: [<the list, as strings>]}}` and `php-version: ${{ matrix.php }}`.
- `auto` for a package: every PHP minor from the floor of `require.php` (the lowest `X.Y` in it) up to the latest the setup knows, as strings, contiguous, first the floor, including at least `8.4` and `8.5` for `^8.3`. The DDEV `php_version` and `config.platform.php` do not decide it. `auto` for an app: no matrix, the single version of the S7 rule.
- The one `composer test` step, the actions and the rest of the workflow are as S7 pins. A change of the matrix plans only the workflow. `MatrixWorkflowPassesActionlint` runs actionlint 1.7.7 on the result.

## 4. Package skeleton and PHPStan paths (rows 9, 10, 25)

- Round 3 (F2, amends this section): a Testbench package gets `tests/Pest.php` only when `pestphp/pest` is in `require` or `require-dev`, `tests/Pest.php` does not exist, there is no `tests/TestCase.php`, and no file under `tests/` calls `uses(`. Then it is a created file in the plan: `declare(strict_types=1);`, `use Orchestra\\Testbench\\TestCase;` (Pint wants the import), `pest()->extend(TestCase::class)->in(__DIR__);`, valid PHP. Otherwise nothing is planned and nothing printed about it. An existing file is never replaced, changed or called a hand edit; a file the person edits after the first run is left alone (`No changes`). An app gets none.
- `phpstan.neon` for a package (when the setup manages it): the paths are `src` (when it exists), `tests` (when it exists as a directory, or when this run creates `tests/Pest.php`), `workbench/app` (when it exists), in that order, never a directory that is missing. A PHPUnit-only package without a tests folder lists `src` only; a Pest package gets `tests` because its Pest.php is planned. The rerun does not change the file. An app keeps the S7 paths.

## 5. CLAUDE.md before Boost (row 3)

When `CLAUDE.md` is missing and Claude Code is the agent (`boost.json` absent, or its `agents` lists `claude_code`), the setup plans an empty `CLAUDE.md` as a created file (app and package alike). It is never edited once it exists, whoever wrote it (R4); what Boost writes into it later is left alone. With `AGENTS.md` present and `CLAUDE.md` missing it still creates `CLAUDE.md` and prints a line naming both files. Declined plans write nothing.

## 6. Output (rows 13, 16)

- After `Runner:` and the profile line, every run lists each option as `  <key>: <value> (profile)` or `  <key>: <value> (default)`, for `runner`, `house_style`, `phpstan_level`, `monitoring`, `ci`, `test_database`, `php_matrix` (`auto`, or the list joined by `, `) and `test_pins` (`none`, or `NAME=value` joined by `, `). With no profile the existing "No profile found ... using the defaults" lines stay, each option line starts with the same `<key>: <value>`, and the three new keys are listed.
- The summary line is `<N> changes planned.` or `1 change planned.` (then the instruction to run the setup). The words "would change" are gone from the output.
- On every run, unless `.claude/settings.json` has `enabledPlugins["laravel-claude-skills@laravel-claude-skills"]` true, the output contains `/plugin marketplace add michtio/laravel-claude-skills` and `/plugin install laravel-claude-skills@laravel-claude-skills` (Claude Code's documented commands, https://code.claude.com/docs/en/discover-plugins). They are printed text, not a `Run:` action; the setup writes no `.claude/settings.json`; the exit code does not change.

## 7. README and docs (rows 1, 2, 3, 4, 11, 13, 16, 32, merge rule)

Checked by `test_s9b_docs.py`, by section. README: a level-2 Install section with level-3 sections for an app and for a package, each with `claude-skills:setup`, then `boost:install`, then `claude-skills:setup --check`, the package one through `vendor/bin/testbench`; why the second setup run exists (Boost resets `.mcp.json`); CLAUDE.md before Boost and the AGENTS.md effect; the non-interactive Boost recipe (`boost.json` with `agents`, `packages`, `"cloud": false`, `boost:install` with `--no-interaction`); the VCS repository block, `dev-main`, until the first tag, the lock pins the commit; for a package `workbench:install --basic --devtool` then `pint workbench`; the plugin install commands (and the Agents section pointing to them); `boost:update` after a DDEV PHP change; merge with a merge commit, never a squash. `docs/profile.md`: the three keys with their defaults in backticks, the `test_database` values, the four pin names and that the database pins cannot be named, the `php_matrix` default from the `require.php` floor, the DDEV red "Failed to execute command" line after `--check`, the `changes planned` wording.

## 8. Agents (rows 17, 23, 29, 65, 67, 69, merge rule)

Checked by `test_s9b_agents.py`, one paragraph or bullet per rule. Gate writer: before `git add` it runs the project's formatter (Pint) on its own test files only, never a bare or project-wide run, reruns the tests, and the hand-back has a `Format:` line; every public name it chose itself (class, method, config key, env var, constant) is listed under Open, and the hand-back's Open line says so. Builder: with no todo tool it lists the steps in its first message and marks them in the hand-back (`Todo:` line), never skipping the list silently; the Git bullet lets a brief ask for a push and a PR on the slice branch (never the main or default branch, never a force push), and without the ask it does not push; the hand-back has a `PR:` line that says the PR merges with a merge commit; a gated PR merges with a merge commit, never a squash, because a squash removes the gate commit; a check that is a tripwire by design (a heuristic with no fixed point) stops after the Importants one test row can close, lists the rest as documented false negatives or positives in the docblock, does not reopen the design, and its rounds count against the cap of 3.

## 9. The real run (rows 3, 6, 8, 9, 10, 13, 16)

`tests/gate/test_s9b_ddev.py` sets up `tests/Fixtures/s9b-package` (empty `src`, no tests directory, no CLAUDE.md, profile `test_database: ddev`, `ci: true`, `php_matrix: [8.3, 8.4]`) in its own DDEV project on MySQL 8.0 and PHP 8.4: setup exits 0 and writes the pieces of sections 1 to 6; `ddev restart` creates `s9b_package_test`; a rerun says `No changes`; `composer test` (Pint, PHPStan, Pest, secret scan) is green and its test asserts the suite runs on the MySQL database `s9b_package_test` and the dev database `db` is untouched. The project is deleted afterwards.

## 10. Amendments to earlier gate files

None remain. Round 1 amended two assertions (`ProfileLevelTest`, `ProfileRound3Test`) from `['src']` to `['src', 'tests']`; round 3's rule (Pest.php only for a Pest package) makes the fixture package, which has no Pest, list `['src']` again, so both are back to their original text.

## 11. Red on the base commit, green by design

Run on `eb1ab43` (main after S9), the new files fail for the reasons the missing features explain, except the tests below, which pass today on purpose (each pins a rule the fix must keep, and each has a red partner above it): ones that only assert a negative or an unchanged state (declined plan writes nothing, an existing CLAUDE.md or Pest.php untouched, an app gets no Pest.php, app paths unchanged, enabled plugin prints no install step, no settings.json written, the workflow keeps one `composer test`, an app on DDEV with `test_database: ddev` equals `auto`, `auto` plans nothing for a package, a package workflow without the key has no services, the other pins stay forced, the two startup-budget checks).

## 12. Project files rule (row 83)

Team rule, ruled by the owner: everything ships with README, docs, CHANGELOG and LICENSE where they apply, updated in every slice that changes behavior. Boost's foundation line "only create documentation files if explicitly requested" works against it. Checked by `test_s9b_project_files.py`:

- A pack guideline in `resources/boost/guidelines/` states the rule: the four files, "where they apply", updated in every slice that changes behavior, without waiting to be asked, and that it wins over Boost's "explicitly requested" line. It sits outside the `@if ($houseStyle)` block of `core.blade.php` (or in its own file), so switching house style off never removes it.
- `laravel-builder`: a named section or a step after the layers updates the README and the CHANGELOG for the slice before the checker and the hand-back, says it does not treat Boost's line as a reason to skip them, and the hand-back has a `Project files:` line (README, CHANGELOG and docs touched, or `none` with the reason).
- `laravel-review-checker`: the conventions lens checks that a diff that changes behavior updates the README, docs and CHANGELOG, and a missing update is an Important finding.
- The pack's own `CHANGELOG.md` at the repo root: `# Changelog`, a `## [Unreleased]` section with Keep a Changelog `###` headings and entries, mentioning `1.0.0-beta.1`. `LICENSE` stays.
- US spelling and no em dashes in what this slice adds (CHANGELOG, the guideline, the three agent files, README, docs/profile.md).

## 13. Round 3 (PR review findings)

Gate files: `tests/Profile/S9bRound3Test.php`, `S9bPackageSkeletonTest.php` (Pest added to the Pest cases). Same lock rules.

1. **F2.** Section 4 above: Pest.php only for a Pest package that has no base case yet; PHPStan `tests` follows that file.
2. **F1.** A `php_matrix` item or a `test_pins` value with a trailing newline (`"8.4\n"`, `"file\n"`, `"env\n"`) is refused as `laravel.php_matrix.<index>` or `laravel.test_pins.<NAME>`, exit 1, nothing written.
3. **Order.** The printed options and `Profile::effective()` use one order whatever the profile sets: `runner`, `house_style`, `phpstan_level`, `monitoring`, `ci`, `test_database`, `php_matrix`, `test_pins`. Amended 2026-11-28 (skills-gaps row 184, owner ruling: new profile options join `effective()`): `Profile::effective()` adds `ci_services` last, default the empty list.
4. **Symlinks.** A symlinked `tests` folder (package with Pest) or a symlinked `CLAUDE.md` (to a file outside, or dangling) is refused at plan time like the other owned paths: exit 1, a message naming the path and `symlink`, nothing written, the outside target untouched, no Pest.php plan shown.
5. **Server twin.** With a pin set to `env`, a hand-written `<server>` twin for it whose value is not the standard one (`sync` for `QUEUE_CONNECTION`) is reported as `edited by hand: phpunit.xml` before the setup removes it, also when the setup wrote the twin and the person changed it. A standard-value twin is removed without that report.
6. **Same engine.** With `test_database: ddev` on a package, the CI database service and the forced pins follow the DDEV database block; where the block is missing or lacks a version they follow what the installed DDEV reports (round 4, section 14). The local connection and the CI engine always agree.
7. **Own DB keys.** A `DB_HOST`, `DB_PORT`, `DB_USERNAME` or `DB_PASSWORD` the person set in `.ddev/config.yaml` `web_environment` is never silently replaced: either the override leaves that key out (kept), or the setup exits non-zero naming the key and writes nothing. `.ddev/config.yaml` is never changed. The keys the person did not set are still written.
8. **Wording.** This file names no private consumer project.

## 14. Round 4 (the engine comes from the installed DDEV)

Gate files: `tests/Profile/S9bRound4Test.php`, `tests/Profile/ProfileTestCase.php` (a default reader), `S9bRound3Test.php` (item 6 rewritten), `tests/gate/test_s9b_ddev.py` (`NoDatabaseBlockFollowsRunningDdev`). Same lock rules. This replaces round 3's "no block means MariaDB 10.11": DDEV's default moves between versions (v1.25.6 reports `mariadb:11.8`), so no fixed number is right.

- **The reader.** `Michtio\LaravelClaudeSkills\Setup\DdevDatabaseSource` is an interface with `read(string $root): ?array`, returning `['type' => 'mariadb'|'mysql'|'postgres', 'version' => '<X.Y>']`, or null when nothing can be read. It is resolved from the container, so a test binds its own (`$this->app->instance(...)`). The real one tries the running project (`ddev describe -j`, `raw.database_type` and `raw.database_version`), then the default `ddev config --help` prints (`--database ... (default "mariadb:11.8")`). Inside the web container, `DDEV_DATABASE` (for example `mariadb:11.8`) carries the same value and is a valid source there; the gate does not pin which source the real reader uses.
- **When it is read.** Only for a package on `test_database: ddev`, and only when `.ddev/config.yaml` has no `database` block, or a block with a type and no version (and, for the version, only when the type is not postgres). A block with type and version, and a version-less postgres block, never consult it. With `test_database` not `ddev` it is never read.
- **No block.** Type and version come from the reader: `DB_CONNECTION` (`mariadb`, `mysql`, `pgsql`) in both the forced `<env>` and the `<server>` twin, the CI service image `<type>:<version>` with `MARIADB_DATABASE`, `MYSQL_DATABASE` or `POSTGRES_DB` set to `<slug>_test` (quoted), the hook for that engine, and `DB_PORT` 3306 or 5432 in the override. When the reader returns null the setup exits 1 with a message holding `database:` and `.ddev/config.yaml` (asking for an explicit block), with `--check` and `--yes`, with CI on or off, and writes nothing.
- **A version-less block (Open choice, picked by the gate writer: read it, same type only).** The reader fills the version when it reports the same type (`mysql` block and a reader that says `mysql 8.0` gives `mysql:8.0`; `mariadb` and `mariadb 11.8` gives `mariadb:11.8`). When it reports another type (a `mysql` block and a default of `mariadb 11.8`, since only a running mysql project can tell a mysql version) or nothing, the setup exits 1 with a message holding `version` and `.ddev/config.yaml`, nothing written. The owner may prefer "always require a version"; that is a one-line change to these two tests.
- **Postgres.** A version-less postgres block keeps the existing default (`postgres:17`, `DB_CONNECTION=pgsql`) and never consults the reader. No source for a DDEV postgres default was found.
- **Rerun.** A rerun with the same reader changes nothing; a reader that later reports another version plans only the workflow (and pins when the engine changes), never "edited by hand".
- **Real DDEV.** `NoDatabaseBlockFollowsRunningDdev` builds a second package project on DDEV's own default database, removes the `database` block `ddev start` wrote out, runs the setup, and asserts the CI service image is `<database_type>:<database_version>` from `ddev describe -j` on the host and the pin matches. No number is named.
- **`"laravel": []`.** PHP encodes an empty array as a JSON list, and an empty list is accepted as no options (also `{}`); a non-empty list is refused as `Invalid profile .ai/skills-profile.json: laravel`, exit 1, nothing written.
- **Test default.** `ProfileTestCase::setUp` binds a reader reporting `mariadb 11.8` whenever the interface exists, so earlier tests with a no-block DDEV package never shell out; `fakeDdevDatabase($value)` rebinds it (`null` unreadable, `false` fail if consulted).
