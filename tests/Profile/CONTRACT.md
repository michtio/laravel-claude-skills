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
| `phpstan_level` | integer 0 to 10 | `8` | Validated and stated. Its effect on files is not pinned by this gate. |
| `env_schema` | boolean | `false` | Validated and stated. Its effect on files is not pinned by this gate. |
| `monitoring` | `none`, `sentry`, `nightwatch` | `none` | `sentry` plans `composer require sentry/sentry-laravel`, `nightwatch` plans `composer require laravel/nightwatch` (section 5). `none` plans nothing and never removes a package. |
| `ci` | boolean | `false` | `true` plans `.github/workflows/claude-skills-gate.yml` (section 7). |

Output, on every run (plan, `--check`, `--yes`, "No changes" included), after `Runner: ...` and before the plan:

- no profile file: the line `No profile found at .ai/skills-profile.json; using the defaults:` followed by one line per option, indented, as `  <key>: <value>` (booleans as `true`/`false`, e.g. `  runner: auto`, `  phpstan_level: 8`). The substrings `No profile found at .ai/skills-profile.json` and `using the defaults` and `<key>: <value>` for all six keys are pinned.
- a profile file: the line `Profile: .ai/skills-profile.json`, and neither `No profile found` nor `using the defaults` anywhere.
- an unknown key inside `laravel`: the line `Ignoring unknown profile key: laravel.<key>`. Unknown keys anywhere else, and the keys themselves, are kept and ignored without a line.

`Profile` API (`src/Profile/Profile.php`): `load(string $root): Profile`, throws `ProfileException` on an invalid file; `exists(): bool`; `laravel(): array` (the table above); `steps(): list<array{name: string, command: string}>`; `verdicts(): array` (the profile's own, as written; `[]` when none).

## 3. Validation

An invalid profile is refused, whatever the options (`--check`, `--yes`, interactive): exit code 1, the output holds `Invalid profile .ai/skills-profile.json: <dotted field path>: <reason>`, and nothing is written (no file created or changed, state file included). The field path is dotted, list items by index: `builders.0.command`, `setup.steps.1.command`, `verdicts.vendor/pkg.use`, `laravel.house_style`. Only the offending field is named. `Profile::load` throws `Michtio\LaravelClaudeSkills\Profile\ProfileException` (a `RuntimeException`) with the same message.

Refused:

- not JSON, not a JSON object, empty file (path `.ai/skills-profile.json`);
- `version` missing or not the integer 1; `gate_tests` not `locked` or `builder-written`; `builders` not a list, an item without string `name` or `command`, `timeout_minutes` not a number above 0; `managed_by` or `setup` not an object; `setup.steps` not a list, a step without string `name` or `command` (the schema's rules);
- `laravel` not an object (a JSON list is not an object); `laravel.runner` not one of `auto`, `ddev`, `host`; `laravel.house_style`, `laravel.env_schema`, `laravel.ci` not a JSON boolean (a string, an integer or null is refused); `laravel.phpstan_level` not an integer 0 to 10 (a string `"8"` or a float `7.5` is refused); `laravel.monitoring` not `none`, `sentry` or `nightwatch` (a boolean is refused);
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

- `schema/skills-profile.schema.json` is the Craft pack's file, byte for byte: `michtio/craftcms-claude-skills`, `main` at `48f0c241db45bacb0e9d6668afaeafb6473a7143` (merge of PR #32; the file is not in the v1.31.0 tag), blob `c199e01ba7112a4b0f1ae2d9dec47ebb9d6227e9`, sha256 `69cae85225237022d729e4020c3c1b74d7e2d9decb74cbf0e702d48114d05036`. The builder copies it (`git -C <craft repo> show main:schema/skills-profile.schema.json`), never edits it.
- `docs/profile.md` names the path `.ai/skills-profile.json`, `claude-skills:setup` and `--check`; every property name of the schema in backticks (`version`, `managed_by`, `gate_tests`, `builders`, `name`, `command`, `timeout_minutes`, `setup`, `steps`, `verdicts`, `craft`, `answers`, `choices`, `hosting`, `passwordless`, `dev_root`, `chrome_devtools_mcp`, `craft_mcp`, `laravel`, `tool`); the six `laravel` keys, each on a line that also holds its default in backticks (`` `auto` ``, `` `true` ``, `` `8` ``, `` `false` ``, `` `none` ``, `` `false` ``); the enum values in backticks (`auto`, `ddev`, `host`, `sentry`, `nightwatch`, `none`, `locked`, `builder-written`); the phrases "unknown keys", "precedence", "default", "rerun", the workflow path and `composer test`; that a profile verdict replaces the register row. No model or vendor name.

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
