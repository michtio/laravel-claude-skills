# The project profile

`claude-skills:setup` reads an optional profile, `.ai/skills-profile.json`, committed in your repository. The profile chooses the setup's options, adds extra setup steps, overrides package verdicts and names outside builders. It can be written by hand or by a team tool: the setup only reads it, never writes, reformats or deletes it.

With no profile, the setup uses the documented defaults below and says so on every run.

## Install and run

The full install order per project kind (the setup, `boost:install`, the setup again), requiring the unreleased pack and the agents plugin are in the [README](../README.md#install).

```sh
# DDEV
ddev composer require --dev michtio/laravel-claude-skills
ddev artisan claude-skills:setup

# Host
composer require --dev michtio/laravel-claude-skills
php artisan claude-skills:setup
```

In a Testbench package, run `vendor/bin/testbench claude-skills:setup` (or `ddev exec vendor/bin/testbench claude-skills:setup`).

Every run first prints what it detected, then every effective option with its source, `(profile)` or `(default)`, for example `  runner: ddev (profile)` and `  test_pins: none (default)`, and the two Claude Code commands that install the agents (until `.claude/settings.json` enables the plugin). The setup then prints every change as a diff, every command it will run, and asks once. Options:

- `--check`: exit 1 when anything would change (a file, a command, a pending extra step), 0 when nothing would. It never asks, never writes and never runs anything. Use it in CI or from a team tool. Under DDEV (`ddev artisan claude-skills:setup --check`), DDEV follows that expected exit 1 with its own red `Failed to execute command ... exit status 1` line: that is DDEV reporting the exit code, not a crash. The plan before it ends with `<N> changes planned.` (`1 change planned.` for one).
- `--yes`: apply without asking.
- `--path=<dir>`: the project root.

Every run also prints suggested `.claude/settings.json` content: one exact `permissions.allow` rule for the gate command (`Bash(composer test)`, or `Bash(ddev composer test)` on DDEV), and the agents plugin's marketplace and `enabledPlugins` entry. It suggests no wildcard rule: `ddev exec` hands its arguments to the container's shell, which expands `$(...)` even inside single quotes, so a rule such as `Bash(ddev exec vendor/bin/pest *)` would approve any command; on the host, `pest -c <file>` can skip the test pins and `pint` can rewrite files it should not. The setup never writes `.claude/settings.json`: Claude Code's settings are yours, so merge what you want.

Some lines change nothing on disk and say what to do instead:

- Boost output under the Testbench skeleton (`vendor/orchestra/testbench-core/laravel`): `boost:install` ran before the setup pointed `testbench.yaml` at the package root; run `boost:install` again after the setup.
- On DDEV, when `CLAUDE.md` names another PHP version than DDEV's `php_version`: run `boost:update` in the runner's form.
- A hand-edited setup `phpstan.neon` next to your `.dist` config (see PHPStan below).
- An existing package suite moving to the DDEV database (see Test database below).
- When the suite runs on a database server: every workflow under `.github/workflows/` the setup does not own that runs the tests without a `services:` block, by name. The setup changes none of them; add a database service to each before the next push.

## Example

```json
{
    "version": 1,
    "managed_by": {"tool": "team-tool", "version": "1.2.0"},
    "gate_tests": "locked",
    "builders": [
        {"name": "local", "command": "run-local-builder --brief {brief}", "timeout_minutes": 30}
    ],
    "setup": {
        "steps": [
            {"name": "check the local machine", "command": "sh scripts/check-machine.sh"}
        ]
    },
    "verdicts": {
        "maatwebsite/excel": {
            "use": "avoid",
            "reason": "Exports here are large and plain; we stream them.",
            "conditions": "Use openspout/openspout instead.",
            "checked": "2026-11-27"
        }
    },
    "laravel": {
        "runner": "ddev",
        "monitoring": "sentry",
        "ci": true
    }
}
```

## Schema

The file follows `schema/skills-profile.schema.json`, the same file the Craft pack (`craftcms-claude-skills`) ships, byte for byte. One profile can serve both packs: each reads its own keys.

Unknown keys are kept and ignored, at every level. The setup names an unknown key inside `laravel` (`Ignoring unknown profile key: laravel.<key>`), so a typo there is not silent; unknown keys anywhere else pass without a line.

An invalid profile is refused before anything is planned: the setup exits 1 with `Invalid profile .ai/skills-profile.json: <field>: <reason>`, where `<field>` is the dotted path of the offending value (list items by index, for example `setup.steps.1.command` or `verdicts.vendor/package.use`), and writes nothing.

## Top-level keys

| Key | Type | Read by | Meaning |
|---|---|---|---|
| `version` | integer, required | setup | The profile format version. Always `1`. |
| `managed_by` | object | nobody (informational) | The tool that wrote the file: `managed_by.tool` and `managed_by.version`, both strings. |
| `gate_tests` | `locked` or `builder-written` | agents | Who writes the gate tests of a slice: `locked`, a separate gate writer whose tests the builder cannot change, or `builder-written`. With no value, the builder uses `locked` when the test suite is isolated (`phpunit.xml` pins `DB_DATABASE` with `force="true"`). `locked` never applies to a suite that is not isolated: the builder then says `Gate flow: builder-written (no isolated suite)`. |
| `builders` | list of objects | agents | Outside builders, tried in order. Each has a `name` (string), a `command` (string) and an optional `timeout_minutes` (a number above 0). |
| `setup` | object | setup | Extra project setup. `setup.steps` is the list of extra steps (below). |
| `verdicts` | object | agents | Package verdicts that take precedence over the package's register (below). |
| `craft` | object | Craft pack | Craft pack keys, ignored here: `craft.answers` (`hosting`, a string; `passwordless`, a boolean; `dev_root`, a string) and `craft.choices` (`chrome_devtools_mcp` and `craft_mcp`, booleans). They are only checked against the schema. |
| `laravel` | object | setup | The Laravel options (below). Ignored by the Craft pack. |

## Laravel options

Each option has a default; a value in the profile takes precedence over the default. With no profile, the setup prints `No profile found at .ai/skills-profile.json; using the defaults:` and lists every option. Any other key under `laravel` is kept, ignored and named in an `Ignoring unknown profile key` line.

| Option | Values | Default | Effect |
|---|---|---|---|
| `runner` | `auto`, `ddev`, `host` | `auto` | Where commands run. `auto` follows detection (DDEV when `.ddev/` exists); `ddev` or `host` takes precedence over detection for every runner-dependent file (`.mcp.json`, the runner guideline, the core override, the test database hook). |
| `house_style` | `true`, `false` | `true` | The house PHP style guideline (PHPDocs on every class and method, `@author`, section headers, strict types). Read by the guideline when `boost:update` composes it; the setup plans nothing for it. |
| `phpstan_level` | integer `0` to `10` | `8` | The level of the `phpstan.neon` the setup writes (see PHPStan below). |
| `monitoring` | `none`, `sentry`, `nightwatch` | `none` | `sentry` plans `composer require sentry/sentry-laravel`, `nightwatch` plans `composer require laravel/nightwatch`, through the runner (`ddev composer require ...` on DDEV). Not planned when the package is already in `require` or `require-dev`, and never for a Testbench package. `none` plans nothing, and the setup never removes a monitoring package. |
| `ci` | `true`, `false` | `false` | `true` writes the CI workflow `.github/workflows/claude-skills-gate.yml` (below). Back to `false`, the setup deletes the workflow if it is still its own output. |
| `test_database` | `auto`, `ddev` | `auto` | `ddev` gives a Testbench package on DDEV the test database an app on DDEV gets (see Test database below); for an app it changes nothing. `auto` keeps a package on in-memory sqlite. |
| `php_matrix` | `auto`, or a list of `"X.Y"` strings | `auto` | The PHP versions the CI workflow tests on (see CI workflow below). |
| `test_pins` | an object of pin name to value or `env` | `none` | Overrides single PHPUnit pins (see Test pins below). Isolation stays the default: every pin the profile does not name stays forced. |
| `ci_services` | a list of service names: `redis` | `none` | Extra service containers for the CI workflow's gate job, beside the database (see CI workflow below). |

An empty list, `"laravel": []` (what PHP's `json_encode` writes for an empty map), counts as no options set. Booleans must be JSON booleans and `phpstan_level` a JSON integer: `"false"`, `0`, `null` or `"8"` are refused.

### Test database

A Testbench package tests on in-memory sqlite by default. With `"test_database": "ddev"` a package on DDEV tests on DDEV's db service instead, as an app does: the setup writes the post-start hook in `.ddev/config.claude-skills.yaml` that creates `<slug>_test` (with a `web_environment` list for DDEV's host, port and credentials, since a package has no `.env` that names them), forces `DB_CONNECTION` (from the DDEV database type: `mysql`, `mariadb`, or `pgsql` for postgres) and `DB_DATABASE=<slug>_test` in `phpunit.xml.dist`, and gives the CI workflow a database service. Run `ddev restart` once so the hook creates the database.

The engine and version come from the `database:` block of `.ddev/config.yaml` when it names both. When it names none, or only a type, the setup asks the installed DDEV (`ddev describe -j` for the project, inside the web container `DDEV_DATABASE`, else the default `ddev config --help` prints), so the pins, the hook and the CI service run what DDEV runs; a version-less block takes the version only when DDEV reports the same type. A version-less `postgres` block uses 17. When DDEV cannot tell, the setup exits 1 and asks for an explicit `database:` block in `.ddev/config.yaml`, writing nothing. When DDEV's default later moves, a rerun plans only the workflow (and the pins when the engine changes). `ddev` on a project that does not run on DDEV (no `.ddev/`, or `"runner": "host"`) is refused with exit 1, and nothing is written.

Moving an existing suite from in-memory sqlite to the DDEV database can break it in two ways, and the setup warns when the package already has tests and the move is not applied yet:

- `already exists`: in-memory sqlite forgets the tables a test creates, MySQL and MariaDB keep them. DDL commits implicitly, so a `RefreshDatabase` transaction cannot undo a `Schema::create()` either, and the next test that creates the table fails with `Table '...' already exists`.
- `Too many connections`: Testbench builds an application per test, and each one leaves its database connections open until the server refuses new ones.

A base `TestCase` handles both: it refuses any database whose name does not end in `_test` (or is not `:memory:`), drops every table before each test, and disconnects every connection when the test's application is destroyed. Point `tests/Pest.php` at it with `pest()->extend(Tests\TestCase::class)->in(__DIR__);` and add the `Tests\` namespace to `autoload-dev`:

```php
<?php

declare(strict_types=1);

namespace Tests;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Orchestra\Testbench\TestCase as Testbench;

abstract class TestCase extends Testbench
{
    protected function setUp(): void
    {
        parent::setUp();

        $database = (string) DB::connection()->getDatabaseName();

        if ($database !== ':memory:' && ! str_ends_with($database, '_test')) {
            throw new \RuntimeException("Refusing to drop the tables of {$database}: not a _test database.");
        }

        Schema::dropAllTables();

        $this->beforeApplicationDestroyed(function (): void {
            foreach (array_keys(DB::getConnections()) as $name) {
                DB::disconnect($name);
            }
        });
    }
}
```

This is for tests that create their own tables. A suite on `RefreshDatabase` migrates inside `parent::setUp()` with `migrate:fresh`, which drops the tables itself: keep the `_test` guard and the disconnects there, and leave out `Schema::dropAllTables()`.

### Test pins

The setup forces the test environment in the PHPUnit file so the suite never reaches the dev database, a real mailer, queue or cache, or a live provider. `test_pins` overrides single pins and nothing else: only `SESSION_DRIVER`, `CACHE_STORE`, `QUEUE_CONNECTION` and `MAIL_MAILER` can be named. The database pins (`DB_CONNECTION`, `DB_DATABASE`, `DB_URL`), `APP_ENV` and the live-provider flags cannot be named, so isolation stays the default; naming one, or a value that is not plain letters, digits, `_`, `.` and `-`, is refused.

```json
"laravel": {"test_pins": {"CACHE_STORE": "redis", "SESSION_DRIVER": "env"}}
```

- A value, such as `redis`, replaces the standard one and stays forced (`force="true"`, with the `<server>` twin for `QUEUE_CONNECTION` and `MAIL_MAILER`).
- `env` writes the pin without force and without a `<server>` twin, with the standard value as its default (`array`, `array`, `sync`, `array`), so a value the shell or `ddev exec env SESSION_DRIVER=file vendor/bin/pest` sets wins, and the default applies when nothing is set. Use it for a gate that runs the same tests under several drivers.
- Changing or removing a pin plans only that line of the PHPUnit file; a rerun reports `No changes`.

`BCRYPT_ROUNDS` is pinned to `4`, forced, as Laravel's app skeleton does, so every hash a test makes stays fast. A `BCRYPT_ROUNDS` the PHPUnit file already sets without `force` (the stock skeleton line) is left as it is; a forced one is owned like the other pins and set to `4`.

## Extra setup steps

`setup.steps` is an ordered list of commands the setup runs after its own work, each with a `name` and a `command`:

- The plan shows them last, after every file diff and every other command, as `Extra step: <name>` followed by `Run: <command>`.
- They run only after you confirm (or with `--yes`), never with `--check`, never when you decline. They run after every file is written and every other command ran, one by one, in order, as `sh -c <command>` from the project root.
- A step that fails (non-zero exit) stops the run with exit code 1: later steps do not run, files already written stay written.
- A step that ran is recorded by exact name and command in `.ai/claude-skills-setup.json`. A rerun plans only steps that are not recorded: a new step, or one whose name or command changed in any way, even by a space. A failed step is not recorded, so the rerun plans it again. Removing a step plans nothing.
- So a team tool that updates other options must not rewrite the text of existing steps (reformat, re-quote, rename): any change to a step's name or command runs that step again.
- A name is one line of plain text and a command plain text: control characters (a carriage return, an escape sequence, NUL and the like) are refused, so a step cannot hide what it runs. A command may hold tabs and newlines; a multi-line command is shown as one block under `Run:`. Steps recorded in `.ai/claude-skills-setup.json` are checked the same way, and a state file with such a step is refused.

## Package verdicts

The package ships a register of verdicts on common Laravel packages (the `laravel-package-verdicts` skill): for each package its use (`use`, `avoid` or `depends`), the reason, the conditions and the date it was last checked. The planner and the builder consult it before proposing or adding a package, cite a verdict as `<package>: <use> (<reason>)`, and ask for a ruling instead of adopting a package it says to avoid; the builder also flags an avoided package already in `composer.json`.

Profile verdicts take precedence over the register. They are matched by package name: a profile entry replaces the register row for that package as a whole (a `conditions` or `checked` it leaves out is empty, not inherited from the row), and a package only the profile names is added. Each entry has:

- `use`: `use`, `avoid` or `depends` (required);
- `reason`: a non-empty string (required);
- `conditions`: a string (optional);
- `checked`: a date as `YYYY-MM-DD` (optional).

The setup writes nothing for verdicts, so changing only a verdict leaves the plan empty.

## PHPStan

The setup manages PHPStan only for a project that is on Larastan (`larastan/larastan` in `require` or `require-dev`) or whose profile sets `laravel.phpstan_level` itself. Any other project gets nothing about PHPStan, so the default level `8` applies only once one of the two holds.

When it manages PHPStan, it writes `phpstan.neon`:

```neon
includes:
    - vendor/larastan/larastan/extension.neon
    - vendor/michtio/laravel-claude-skills/extension.neon

parameters:
    level: 8
    paths:
        - app
        - config
        - database
        - routes
```

- The paths are those of `app`, `config`, `database` and `routes` that exist, in that order; when none exists, `src` if it exists, else `app`. A Testbench package gets those of `src`, `tests` and `workbench/app` that exist, in that order (`tests` also when the same run creates `tests/Pest.php`), so a fresh package with an empty `src` still has files to check and no missing path fails the gate.
- If Larastan is not required yet, the plan adds `composer require --dev larastan/larastan` (`ddev composer require --dev larastan/larastan` on DDEV), run after the other commands and before the extra steps. Larastan is never removed.
- An existing `phpstan.neon`, `phpstan.neon.dist` or `phpstan.dist.neon` that the setup did not write is never changed, and nothing is installed for it: the setup prints `Left alone: <file>` on every run. A `phpstan.neon` the setup wrote earlier is removed (if unchanged) once you add one of your own, so it cannot shadow yours.
- To take PHPStan over, create `phpstan.neon.dist` with your config and delete the setup's `phpstan.neon` in the same change, then run `claude-skills:setup --yes` and commit `.ai/claude-skills-setup.json` with it. `--check` exits 0 after the takeover: the stale record of the deleted file stays until the next real change.
- Shadowing: PHPStan reads `phpstan.neon` first, then `phpstan.neon.dist`, then `phpstan.dist.neon`, so a leftover `phpstan.neon` shadows your `phpstan.neon.dist` and it is never read. When the setup's copy was edited by hand, it is not removed: the setup prints a line saying it shadows your `.dist` on every run until you delete it, and never deletes a hand edit itself. A `phpstan.neon` you wrote yourself (one that includes the `.dist`, PHPStan's local override) is never named.
- The written file is owned like every setup file: a rerun reports `No changes`, and changing `phpstan_level` plans only that file. If you edit or replace it, the plan says `edited by hand: phpstan.neon` and `phpstan.neon: applying replaces your changes with level <n>`; nothing is written without your confirmation. To keep your own config, rename it to `phpstan.neon.dist` or `phpstan.dist.neon`: the setup then leaves it alone.
- With `phpstan/extension-installer` in `require` or `require-dev`, the file has no `includes` block: the installer already includes Larastan and this pack, and including them again makes PHPStan fail with "included multiple times". Adding or removing the installer later plans that change to `phpstan.neon` like any other refresh.

## CI workflow

With `"laravel": {"ci": true}` the setup writes `.github/workflows/claude-skills-gate.yml`, for an application or a Testbench package, whatever the runner. The workflow runs the same gate command as your machine, `composer test` (the script the setup writes), after `composer install`, on every push to the default branch and on every pull request, with read-only repository permissions. The default branch is the one origin's HEAD points to, else git's `init.defaultBranch`, else `main` (also `main` outside a git repository). A newer run cancels an older one for the same pull request; runs on the default branch always finish. It never runs Pint, PHPStan or the test runner on its own: the gate is the one command.

It also installs gitleaks (checksum verified), which the secret scan of `composer test` needs in CI, and, for a suite that runs on MySQL, MariaDB or PostgreSQL (an application, or a package with `"test_database": "ddev"`), starts a database service with the test database.

Extra services follow `ci_services`: `"ci_services": ["redis"]` starts a Redis service (the `redis` image) in the gate job and sets `REDIS_HOST` and `REDIS_PORT` in its env, so a suite that needs Redis runs in CI without a hand edit of the workflow. Any other name is refused. Changing the list plans only the workflow.

The PHP versions follow `php_matrix`. A list runs the job once per version, as a matrix (`fail-fast: false`). With `auto`, the default, a package is tested on every PHP minor from the composer.json require.php floor (its lowest X.Y version) up to the latest the setup knows; the DDEV PHP version does not decide it. With `auto`, an application runs one version, the first of: `php_version` in `.ddev/config.yaml` (and its `config.*.yaml` overrides), `config.platform.php` in `composer.json`, the lowest version `require.php` allows, else 8.4, each reduced to X.Y. Changing the matrix plans only the workflow.

The setup owns the file like every file it writes: the plan shows it as a diff, a copy you changed is reported as `edited by hand: .github/workflows/claude-skills-gate.yml` and is only replaced after you confirm.

## Secret scan

`composer test` runs `.githooks/gitleaks-check`, gitleaks with `.gitleaks.toml`. In CI the workflow installs the pinned gitleaks; without it the step fails there. On DDEV the setup writes `.ddev/web-build/Dockerfile.gitleaks`, which installs the same gitleaks release into the web image (the archive for the image's architecture, checked against gitleaks' own checksums), so the local scan is the CI scan. Run `ddev restart` once to build it. On the DDEV runner, a missing gitleaks inside the web container fails the step and names `ddev restart`; elsewhere (the host, or a project set to the host runner) it skips with a message.

- Scope: locally `gitleaks detect` reads the whole git history, while CI checks out one commit (`fetch-depth: 1`) and scans only that. A secret removed in a later commit still fails the local scan until the history is rewritten.
- A historical false positive (a fixture value in an old commit that reads as a key) goes into `.gitleaksignore`, one finding per line by its fingerprint (`<commit>:<file>:<rule>:<line>`, printed by `gitleaks detect`). Never widen `.gitleaks.toml` for it; changing the config is a security decision.

## Rerun: only the difference

The profile is meant to be updated by a tool and the setup rerun to keep a repository current. A rerun applies only the difference:

- Changing one option plans only what follows from it: `ci`, `php_matrix` and `ci_services` plan only the workflow; `phpstan_level` plans only `phpstan.neon`; `test_pins` plans only the PHPUnit file; `test_database` plans the hook, the PHPUnit file and the workflow; `runner` plans only the runner-dependent files; `house_style` and `gate_tests` plan nothing.
- Rewriting the profile with the same meaning (keys reordered, other formatting, `managed_by` added) plans nothing.
- A rerun on an unchanged project reports `No changes` and `claude-skills:setup --check` exits 0.

## Files created once

Three files are created when they are missing and never touched again, whoever writes into them later:

- `CLAUDE.md`, empty, when Claude Code is one of the agents (`boost.json` is missing or its `agents` lists `claude_code`): Boost writes its guidelines into `AGENTS.md` when `CLAUDE.md` does not exist. When `AGENTS.md` exists without `CLAUDE.md`, the setup says so and leaves `AGENTS.md` alone.
- `boost.json`, so a non-interactive `boost:install --no-interaction` installs for Claude Code, includes this pack's skills and leaves the Laravel Cloud skill off: `{"agents": ["claude_code"], "packages": ["michtio/laravel-claude-skills"], "cloud": false}`. An existing `boost.json` is never changed and never reported as edited by hand.
- `tests/Pest.php` in a Testbench package on Pest (`pestphp/pest` required) whose tests pick no base case yet (no `tests/TestCase.php`, no test file calling `uses(`), extending `Orchestra\Testbench\TestCase` for every test, so a fresh package has a suite to run.

A symlinked `tests` folder in a Pest package, or a `CLAUDE.md` that is a dangling symlink or points outside the project, is refused like the setup's other files: exit 1, nothing written. A `CLAUDE.md` symlink to a file inside the project is left alone.
