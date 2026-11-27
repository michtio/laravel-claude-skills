# Gate contract, slice S9d-1 (laravel-layer): setup, runner and process items

Requirements: R1, R2, R4, R7, R8, R9, R11, R13, R15, R17, R23 (decisions log 2026-11-27: "S9c and S9d", "found defects are fixed, never deferred", R7 amended, row 16, the spatie/guidelines-skills learnings, consolidation before every release, and the S9d split into S9d-1 and S9d-2, marked pending in the log). Source: `internal-docs/skills-gaps.md`, rows 1 to 145 plus S11-1 and S8-1 as of this gate. Plan: slice S9d in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`, split as the plan allows: S9d-1 is setup, runner and process items; S9d-2 is skill content (pitfalls, verdicts, skill notes) and gets its own gate.

The gate is written before the builder starts. The builder implements to this contract and never edits `tests/S9d1/`, the gate files below, or any other file under `tests/`, except through the gate writer. The builder closes the rows in `skills-gaps.md` with the commit that fixed them (this file does not edit it). Everything earlier slices pinned stays: in particular S9b section 6 (the setup writes no `.claude/settings.json`), S9b section 4 (a Pest package's `tests/Pest.php` extends Testbench's case directly), S6's stock `BCRYPT_ROUNDS` kept unforced (`SetupIsolationRound2Test`), and the S9c agent rules.

Run, from the repo root, one at a time:

```
ddev exec vendor/bin/pest --filter=S9d1                  # the PHP gate (tests/Profile/S9d1*Test.php)
python3 -m unittest discover -s tests/gate               # includes test_s9d1_*.py; test_s9d1_tools.py needs ddev (or CI) and the network
sh scripts/check.sh
ddev exec vendor/bin/pest
```

Gate files: `tests/Profile/S9d1RunnerTest.php`, `tests/Profile/S9d1GitleaksTest.php`, `tests/Profile/S9d1OutputTest.php`, `tests/gate/test_s9d1_docs.py`, `tests/gate/test_s9d1_agents.py`, `tests/gate/test_s9d1_tools.py`, and the fixture `tests/Fixtures/s9d1-dead-code/S9d1Unused.php`.

## 1. Tinker under DDEV (row 5)

`ddev exec` joins its arguments into one double-quoted `bash -c` string, so `$n` in `tinker --execute '$n = 41; ...'` is expanded by the container shell ("n: unbound variable"). Checked on DDEV v1.25.6: `ddev exec php -r '$n = 41; echo $n + 1;'` fails that way, `ddev exec --raw -- php -r '...'` prints 42. `ddev artisan` is a DDEV custom command with `## ExecRaw: true` (its script in `~/.ddev/commands/web/artisan`; https://docs.ddev.com/en/stable/users/extend/custom-commands/: "Use `ExecRaw: true` to pass command arguments directly to the container as-is"), so `ddev artisan tinker --execute '...'` is safe and stays allowed.

- The DDEV runner guideline (package, and an app on a non-laravel DDEV type) has a tinker line, carries no `ddev exec ...tinker ... --execute` that is not `ddev exec --raw --`, and its tinker form contains `--raw --` or reads the code from stdin (`tinker <`).
- It names Boost's `tinker` MCP tool (a line with `` `tinker` `` and "MCP" or "tool").
- The derived core override (`.ai/guidelines/boost/core.blade.php`) carries no such `ddev exec` form either (Boost 2.10.4's core guideline has `tinker --execute 'Your::code();'` through `artisanCommand`).

## 2. The package runner guideline (row 15)

For a Testbench package, host and DDEV: a line names `src/` with the composer autoload namespace (`Example\Package\` for the fixture); a line says `make:` generators do not write into `src/` (with `laravel: ./` they write under the package root's skeleton paths); a line replaces `php artisan test` with `vendor/bin/pest` in the runner form (`` `vendor/bin/pest `` or `` `ddev exec vendor/bin/pest ``); `test --compact` is gone; "Laravel package" appears in the DDEV form too. The README's Testbench package section mentions `boost.enforce_tests`: Boost 2.10.4 decides test enforcement with `config('boost.enforce_tests')`, else by running `artisan test --list-tests` in `base_path()` (`vendor/laravel/boost/src/Console/InstallCommand.php`, `determineTestEnforcement()`), which a package has no `artisan` for.

## 3. testbench.yaml edited as text (row 14)

Fixture: what `workbench:install --basic --devtool` writes (orchestra/workbench v11.3.0, `src/Console/stubs/testbench.yaml`, placeholders filled). After the setup every original line except the owned `laravel:` line is in the file unchanged and in order (the commented `providers:` item, the blank lines), `providers: null` never appears, `laravel` parses to `./` and `env.APP_DEBUG` to true. A rerun says `No changes`. A comment inside an existing `env:` map, and one before it, are kept when `APP_DEBUG` is added.

## 4. gitleaks in the DDEV container (rows 12, 124)

- Every project on the DDEV runner (app and package) gets `.ddev/web-build/Dockerfile.gitleaks`, shown in the plan: it installs gitleaks `8.30.1` (the release the CI workflow pins), chooses the archive by `TARGETARCH`, and checks it with `sha256sum -c` against gitleaks' own checksums (`gitleaks_8.30.1_checksums.txt`): linux_x64 `551f6fc8...70eb` (the workflow's value) and linux_arm64 `e4a487ee...b080`. DDEV merges `.ddev/web-build/Dockerfile.*` into the web image and exposes `$TARGETARCH` (https://docs.ddev.com/en/stable/users/extend/customizing-images/); `ddev restart` builds it. A rerun says `No changes`. The host runner gets none.
- `.githooks/gitleaks-check` inside DDEV (`IS_DDEV_PROJECT=true`, which DDEV sets in the web container) without gitleaks exits non-zero naming `ddev restart`, so a local `composer test` there never passes without the scan. On the host it still skips with its message (S6, kept).

## 5. Suggested Claude Code permissions (row 16, owner ruling)

Every run prints, after a line naming `.claude/settings.json`, a JSON object whose `permissions.allow` list holds the gate command in the runner's form: `Bash(composer test)` on the host, `Bash(ddev composer test)` on DDEV (rule syntax: https://code.claude.com/docs/en/permissions, "`Bash(npm run build)` matches the exact command"). No rule is `*`, `Bash`, `Bash(*)` or `mcp__*`, and none mentions tinker. The file is never written; an existing one stays byte for byte; a `No changes` run still prints it, exit 0.

## 6. Planned count equals applied count (row 129)

On a fresh app, a fresh DDEV package, and a DDEV package switched to `test_database: ddev` with `ci: true` (the field case), the `N` of `N changes planned.` from `--check` equals the `N` of `Applied: N changes.` from `--yes` on an identical copy. Today the plan leaves the state file out and the apply counts it (7 against 6).

## 7. Boost under the skeleton (row 1) and the boost.json seed (row 4)

- A package whose `vendor/orchestra/testbench-core/laravel/` holds `CLAUDE.md`, `AGENTS.md` or `.claude/skills/...` gets a line naming that path and `boost:install`. Without them, no such line.
- A project without `boost.json` gets it as a created-once file: exactly `{"agents": ["claude_code"], "packages": ["michtio/laravel-claude-skills"], "cloud": false}` (the README recipe; `cloud` and `packages` are keys of Boost 2.10.4's `Support/Config.php`). An existing `boost.json` is never changed or called a hand edit. This also settles row 1's "boost.json missing after the setup ran".

## 8. boost:update after a DDEV PHP change (row 32)

Set up at DDEV `php_version: "8.4"` (CLAUDE.md with Boost's "running on PHP 8.4" line), then changed to `8.3`: the next run prints the runner form, `ddev artisan boost:update` (app) or `ddev exec php vendor/bin/testbench boost:update` (package). Unchanged: no `boost:update` in the output. How the change is detected is the builder's.

## 9. PHPStan ownership (rows 41, 51)

- After the takeover (`phpstan.neon.dist` created, the setup's `phpstan.neon` deleted, its record still in the state file) `--check` exits 0, prints `Left alone: phpstan.neon.dist`, and plans nothing.
- A setup-written `phpstan.neon` that was edited by hand, next to a `phpstan.neon.dist`, gets a line with "shadow" naming both files, on this run and the next. PHPStan reads `phpstan.neon` first, then `phpstan.neon.dist`, then `phpstan.dist.neon` (https://phpstan.org/config-reference). A `phpstan.neon` the person wrote (for example one that includes the `.dist`, PHPStan's local-override pattern) or no `.dist` at all gets no such line. The setup does not delete the edited copy (deleting a hand edit is not this gate's call; see Open).
- docs/profile.md PHPStan section: take over by creating `phpstan.neon.dist` and deleting `phpstan.neon` in the same change; the shadow rule (read first).

## 10. Moving an existing suite to the DDEV database (row 128)

A DDEV package with a test file, set up on sqlite, whose profile now says `test_database: ddev`: one output line names `test_database`, tables and connections, and `docs/profile.md`. No line for a package without tests, nor after the move is applied. docs/profile.md Test database section: `already exists` (MySQL keeps tables a per-test schema creates; DDL commits implicitly), `Too many connections` (Testbench builds an app per test), the TestCase pattern with `beforeApplicationDestroyed`, and the `_test` name guard.

## 11. BCRYPT_ROUNDS (row 133)

A PHPUnit file the setup writes with no `BCRYPT_ROUNDS` gets `<env name="BCRYPT_ROUNDS" value="4" force="true"/>` (app `phpunit.xml`, package `phpunit.xml.dist`); the rerun exits 0. A stock unforced `BCRYPT_ROUNDS` stays as S6 pins it.

## 12. Other workflows and the real database (row 140)

With `test_database: ddev`, every workflow under `.github/workflows/` the setup does not own that runs the tests (`vendor/bin/pest` here) with no `services:` is named in the output; one that runs no tests (`pint --test`) or has a service is not; none is changed. On sqlite, none is named.

## 13. README and docs (rows 12, 15, 16, 41, 51, 124, 127, 128; owner rulings)

`test_s9d1_docs.py`: a README section whose heading names skills.sh with `npx skills add michtio/laravel-claude-skills`; a README section whose heading names Spatie with `spatie/guidelines-skills`, `"house_style": false` and `boost:install`; `enforce_tests` in the Testbench package section; docs/profile.md sections 9 and 10 above; a section whose heading names the secret scan, with `.ddev/web-build/Dockerfile.gitleaks`, `ddev restart`, one line on history (local `gitleaks detect` reads the git history, https://github.com/gitleaks/gitleaks/blob/v8.30.1/README.md "uses the `git log -p` command") against CI's single checked-out commit, and one line on `.gitleaksignore` by fingerprint (same README, ".gitleaksignore"); one line that the setup prints suggested `.claude/settings.json` permissions and never writes it; the boost.json seed with `"cloud": false` under Files created once. CHANGELOG `[Unreleased]` names `Dockerfile.gitleaks`, `boost.json`, `.claude/settings.json`, `BCRYPT_ROUNDS`, `skills.sh` and consolidation. No em dashes in README, docs/profile.md, CHANGELOG (kept).

## 14. R7 as amended: user-facing docs never cite tests

No tracked user-facing Markdown (README, CHANGELOG, `docs/**/*.md`, and the shipped `resources/boost/**/*.md`, which consumers read and which name paths that do not exist in their projects) names a test file of the pack (a tracked `tests/**Test.php` or `tests/**/test_*.py`, by path or file name). Red today on three pitfall references (`pii-logs.md`, `edge-validation.md`, `transactions.md`: "Its proof is `tests/PHPStan/Rules/...RuleTest.php`"). The paired case: the consumer example in `docs-claims.md` (`tests/Feature/Payments/PaymentWebhookTest.php`, not a pack file) stays allowed.

## 15. skills.sh (owner ruling)

`test_s9d1_tools.py` `SkillsShInstall`: `npx -y skills@1.8.1 add <git archive of HEAD> --skill '*' -a claude-code -y --copy` (in DDEV, or on the CI runner) exits 0 and installs exactly the skills under `resources/boost/skills/` with their `references/`. CLI docs read: https://skills.sh/docs, https://github.com/vercel-labs/skills (docs/commands.md and docs/creating-skills.md at v1.8.1; discovery: standard containers, `skills.sh.json` `paths`, then a recursive search when none found; plugin manifests' `skills`). v1.8.1 is 17 days old; v1.9.1 came out today. Green by design today (the recursive search finds both skills): it guards the channel; the README part is red. The check runs on the committed tree, so the builder commits before running it.

## 16. spatie/guidelines-skills coexistence (owner ruling)

`Coexistence`: the pack's skill names and spatie/guidelines-skills 1.1.0's (`spatie-laravel-php`, `spatie-javascript`, `spatie-version-control`, `spatie-security`; https://github.com/spatie/guidelines-skills/tree/1.1.0) do not overlap; with `house_style: false` the pack's core guideline keeps none of the rules Spatie's PHP guideline contradicts (PHPDocs on every method, `@author`, `=========` headers) outside the `@if ($houseStyle)` block. Both packages ship `resources/boost/guidelines/core.blade.php`; Boost keys third-party guidelines by package name (`GuidelineComposer::getThirdPartyGuidelines`, `<vendor/package>/core`), so they do not collide. Green by design (S5 behavior kept); the README section is the red part.

## 17. Unused-public-code check (owner ruling, through the register)

Candidate: shipmonk/dead-code-detector 1.4.2 (2026-09-21, MIT, active, requires `phpstan/phpstan ^2.1.41`, the pack has 2.3.7; Laravel usage providers; "Usage in libraries": mark public API with `@api`; https://github.com/shipmonk-rnd/dead-code-detector). The alternative tomasvotruba/unused-public is archived. Pinned: a register row (`use` or `depends`, the repository URL and `@api` in Reason or Conditions, Checked on or after 2026-11-27); `composer.json` requires it for development; `.github/workflows/ci.yml` has a step `vendor/bin/phpstan ... -c <config>` whose config includes `vendor/shipmonk/dead-code-detector/rules.neon`; that command passes on the pack, and with the planted `tests/Fixtures/s9d1-dead-code` as its only path it fails naming `S9d1Unused::neverCalled`. The dependency is the builder's to add.

## 18. Agents (consolidation mode, row 136)

`test_s9d1_agents.py`. Builder: one line for consolidation mode (no behavior change, nothing under `tests/` changes, the gate is `git diff --quiet <base> HEAD -- tests/` plus the suites green); one line for the consolidation brief (the base commit, the scope or paths, and what to look for: duplicates, dead code, splits); the hand-back template gains `Duplicates merged:`, `Dead code removed:`, `Files split:`, `Tests unchanged:`. Builder (row 140, its half): one line that after a setup change pinning a real test database, every CI workflow that runs the tests can reach it before the first push. Gate writer (row 136): one line that when a shared fixture or boot helper fails first, so every test has the same red reason, it shows the next layer with a stub it reverts, or says in the hand-back (Passability) that the reasons are uniform and how passability was checked.

## 19. Row map

"S9d-1" names the test; "S9d-2" rows are skill content with no test here; "closed" rows were fixed by S9b or S9c and keep their tests.

| Row | Where |
|---|---|
| 1 | open part: `S9d1OutputTest` "warns when Boost wrote into the @testbench skeleton" (3), "prints no skeleton warning"; the boost.json half by row 4 |
| 2, 3, 6 to 9, 11, 13 | closed (S9b) |
| 4 | open part: `S9d1OutputTest` "creates the boost.json seed" (2), "never changes a boost.json that exists" |
| 5 | `S9d1RunnerTest` tinker tests (4), docs none |
| 10 | open part (`tests/TestCase.php`): no test, needs a ruling (Open 1) |
| 12 | `S9d1GitleaksTest` (all), `test_s9d1_docs` `test_secret_scan_section` |
| 14 | `S9d1RunnerTest` testbench.yaml tests (3) |
| 15 | `S9d1RunnerTest` package guideline tests (3), `test_s9d1_docs` `test_package_section_documents_enforce_tests` |
| 16 | settings part: `S9d1OutputTest` section 5 (4), `test_s9d1_docs` `test_suggested_settings_are_documented`; agent part closed (S9c) |
| 17 to 31, 34, 35 | closed (S9b, S9c) |
| 32 | open part: `S9d1OutputTest` "prints the runner-form boost:update" (2), "prints no boost:update hint" |
| 33, 36 to 40, 42 | S9d-2 |
| 41 | `S9d1OutputTest` "warns that a hand-edited phpstan.neon ... shadows" and its negative, `test_s9d1_docs` `test_taking_phpstan_over_...`, `test_the_shadow_rule_is_explained` |
| 43 to 49 | closed (S9c) |
| 50 | pitfall recipe: S9d-2; agent part closed (S9c) |
| 51 | docs and `--check` part: `S9d1OutputTest` "exits 0 on --check after the takeover", the docs tests of row 41; builder part closed (S9c) |
| 52 to 56 | closed (S9c) |
| 57 to 60 | S9d-2 |
| 61 to 88, 90 to 100 | closed (S9b, S9c) |
| 89 | the `laravel/passkeys` register row: S9d-2 (it has no setup part); agent part closed (S9c) |
| 101 to 109 | S9d-2 (109's "runner ddev guideline" note on DDEV's MariaDB default against a mysql CI is content; S9b already makes CI follow DDEV's engine for `test_database: ddev`) |
| 110 | closed (S9c) |
| 111 | pitfall recipe: S9d-2 (the CI or DDEV Redis service it mentions proposes no setup change); agent part closed (S9c) |
| 112 | S9d-2 |
| 113, 114, 116 to 118, 122, 123, 126 | closed (S9c) |
| 115, 119 to 121, 125 | S9d-2 |
| 124 | setup part: as row 12; agent part closed (S9c) |
| 127 | scan scope and the sanctioned route: `test_s9d1_docs` `test_secret_scan_section`; agent part closed (S9c) |
| 128 | `S9d1OutputTest` section 10 (2), `test_s9d1_docs` `test_moving_an_existing_suite_to_the_ddev_database`; the pitfall half (DDL not rolled back, leaked connections) S9d-2 |
| 129 | `S9d1OutputTest` "counts the same changes" (3) |
| 130 | S9d-2 (testing reference: concurrency gates in a package) |
| 131, 132 | S9d-2 |
| 133 | `S9d1OutputTest` "forces BCRYPT_ROUNDS=4" (2) |
| 134, 135 | S9d-2 |
| 136 | `test_s9d1_agents` `test_a_shared_fixture_that_fails_first_is_handled` |
| 137 to 139 | closed (S9c round 2) |
| 140 | setup part: `S9d1OutputTest` section 12 (2); builder half: `test_s9d1_agents` `test_every_ci_workflow_reaches_the_pinned_database_before_the_first_push` |
| 141 to 145 | S9d-2 |
| S11-1 | neither: release runner, slice S11 |
| S8-1 | closed (S9) |

Spatie content items for S9d-2 (no test here): the Artisan command output rule (output, progress, summary), never mixing single-line and multi-line method chaining, `config()` outside config files and service settings in `config/services.php` as a pitfall, event and listener naming hints, an authorization test for every restricted route in the reviewer checklist, and the spatie/guidelines-skills verdict row.

## 20. Red on the base commit, green by design

Run on `984dc33` (main after S9c). Pest: 39 failed for the missing features (no `Dockerfile.gitleaks`; the tinker lines `ddev exec php vendor/bin/testbench tinker --execute`; no settings printout; `7 is identical to 6`; no skeleton warning; no `boost.json` diff; no `boost:update`; `--check` exit 1 after the takeover; no shadow line; no suite warning; no forced `BCRYPT_ROUNDS`; `tests.yml` not named; `providers: null` written). Python: 19 failed (missing README and docs sections, CHANGELOG entries, register row, `composer.json` entry, CI step, agent lines, and the three test citations), plus 3 in `test_s9d1_tools.py` (no CI step).

Green by design (each keeps a rule the change must not break, with a red partner): host gets no Dockerfile; host scan still skips; settings.json never written; no skeleton warning without Boost output; an existing boost.json unchanged; no `boost:update` without a change; no shadow line for the person's own config; no suite warning without tests or once applied; no workflow named on sqlite; `ddev artisan` tinker kept; the R7 paired case; skill names disjoint and the house-style block (S5); no em dashes; `SkillsShInstall` (3: the channel works today through the CLI's recursive search, and the test guards it).

## 21. Constraints for the builder

- The dead-code config cannot analyse `tests/` as it is: a passability probe (shipmonk/dead-code-detector installed temporarily, reverted) reported the locked Pest helpers `ProfileTestCase::diffPaths`, `runLines`, `applied`, `TestCase::boostServer`, `snapshot` and the PHPStan fixtures as unused (Pest closures call them through `$this`). On `src` alone it reported 4: `Profile::laravel`, `Verdicts::FIELDS`, `Verdicts::merged`, `CreatedOnceFilePlanner::path`, `StaticFilePlanner::path`. It reported the planted `S9d1Unused::neverCalled` (`shipmonk.deadMethod`).
- `.ddev/web-build/Dockerfile.gitleaks` joins the setup's owned paths (symlink checks). `test_s9b_ddev.py` restarts its DDEV project after the setup, so the Dockerfile is built there and `composer test` then runs the real scan in that fixture.
- Row 133 must leave an existing unforced `BCRYPT_ROUNDS` alone (`SetupIsolationRound2Test` pins `['4', null]`).
- `tests/Pest.php` for a Pest package stays as S9b pins it (`use Orchestra\Testbench\TestCase;`), which is why row 10 is a ruling.
- No gate test name contains "PHPStan" in any case: `test_s3` and the CI step run `pest --filter=PHPStan` as the rule suite, and the filter matched an earlier draft of these names.
- Row 129 must keep S9b's "1 change planned." for a plan whose only change is an extra step (`S9bOutputTest`): count the state file in neither line unless it is the only change, rather than in both.

## 22. Open (names and wording this gate pins; the owner may rename before the build)

Paths and values: `.ddev/web-build/Dockerfile.gitleaks`; `boost.json` seed content; `IS_DDEV_PROJECT` as the in-DDEV signal; `ddev restart` in the scan's failure; `skills@1.8.1`; `tests/Fixtures/s9d1-dead-code/S9d1Unused.php`. Output wording: the settings JSON follows the first line naming `.claude/settings.json`; the skeleton line names `vendor/orchestra/testbench-core/laravel` and `boost:install`; "shadow" on the PHPStan line; the suite line names `test_database`, tables, connections and `docs/profile.md`. README headings naming "skills.sh" and "Spatie"; a docs/profile.md heading naming "secret scan". Builder hand-back lines `Duplicates merged:`, `Dead code removed:`, `Files split:`, `Tests unchanged:`; the consolidation gate `git diff --quiet <base> HEAD -- tests/`.

Rulings needed (each with a recommendation):

| # | Gap | Recommendation | Fix |
|---|---|---|---|
| 1 | Row 10 wants a planned `tests/TestCase.php`; S9b section 4 ruled against it and locks `tests/Pest.php` extending Testbench's case directly, and a `Tests\` class needs an autoload-dev entry the setup does not write. | Keep S9b; plan `tests/TestCase.php` only as the documented row 128 pattern (docs snippet, no file), close row 10 as superseded. | A one-line ruling in the decisions log; or authorize an S9b amendment and pin TestCase.php plus autoload-dev in S9d-1 round 2. |
| 2 | Row 41 proposes the setup delete an edited `phpstan.neon` after confirmation; the plan never deletes hand edits today. | Warn (pinned here), do not delete. | None if accepted; else a round 2 test for a confirmed deletion. |
| 3 | Row 51 offered docs or `--check`; this gate pins both (`--check` exit 0 after the takeover). A stale record stays in the state file until the next real change. | Accept. | None. |
| 4 | R7 is extended to the shipped skill references (consumers read them; the cited paths do not exist in their projects). | Accept: the builder removes three "Its proof is ..." sentences. | None. |
| 5 | The decisions-log row for the S9d split is marked pending. | Confirm it. | Set the log row to Michael. |
