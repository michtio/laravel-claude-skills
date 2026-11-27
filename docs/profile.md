# The project profile

`claude-skills:setup` reads an optional profile, `.ai/skills-profile.json`, committed in your repository. The profile chooses the setup's options, adds extra setup steps, overrides package verdicts and names outside builders. It can be written by hand or by a team tool: the setup only reads it, never writes, reformats or deletes it.

With no profile, the setup uses the documented defaults below and says so on every run.

## Install and run

```sh
# DDEV
ddev composer require --dev michtio/laravel-claude-skills
ddev artisan claude-skills:setup

# Host
composer require --dev michtio/laravel-claude-skills
php artisan claude-skills:setup
```

In a Testbench package, run `vendor/bin/testbench claude-skills:setup` (or `ddev exec vendor/bin/testbench claude-skills:setup`).

The setup prints every change as a diff, every command it will run, and asks once. Options:

- `--check`: exit 1 when anything would change (a file, a command, a pending extra step), 0 when nothing would. It never asks, never writes and never runs anything. Use it in CI or from a team tool.
- `--yes`: apply without asking.
- `--path=<dir>`: the project root.

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

Each option has a default; a value in the profile takes precedence over the default. With no profile, the setup prints `No profile found at .ai/skills-profile.json; using the defaults:` and lists the five values. Any other key under `laravel` is kept, ignored and named in an `Ignoring unknown profile key` line.

| Option | Values | Default | Effect |
|---|---|---|---|
| `runner` | `auto`, `ddev`, `host` | `auto` | Where commands run. `auto` follows detection (DDEV when `.ddev/` exists); `ddev` or `host` takes precedence over detection for every runner-dependent file (`.mcp.json`, the runner guideline, the core override, the test database hook). |
| `house_style` | `true`, `false` | `true` | The house PHP style guideline (PHPDocs on every class and method, `@author`, section headers, strict types). Read by the guideline when `boost:update` composes it; the setup plans nothing for it. |
| `phpstan_level` | integer `0` to `10` | `8` | The level of the `phpstan.neon` the setup writes (see PHPStan below). |
| `monitoring` | `none`, `sentry`, `nightwatch` | `none` | `sentry` plans `composer require sentry/sentry-laravel`, `nightwatch` plans `composer require laravel/nightwatch`, through the runner (`ddev composer require ...` on DDEV). Not planned when the package is already in `require` or `require-dev`, and never for a Testbench package. `none` plans nothing, and the setup never removes a monitoring package. |
| `ci` | `true`, `false` | `false` | `true` writes the CI workflow `.github/workflows/claude-skills-gate.yml` (below). Back to `false`, the setup deletes the workflow if it is still its own output. |

Booleans must be JSON booleans and `phpstan_level` a JSON integer: `"false"`, `0`, `null` or `"8"` are refused.

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

- The paths are those of `app`, `config`, `database` and `routes` that exist, in that order; when none exists, `src` if it exists, else `app`. A Testbench package gets `src`.
- If Larastan is not required yet, the plan adds `composer require --dev larastan/larastan` (`ddev composer require --dev larastan/larastan` on DDEV), run after the other commands and before the extra steps. Larastan is never removed.
- An existing `phpstan.neon`, `phpstan.neon.dist` or `phpstan.dist.neon` that the setup did not write is never changed, and nothing is installed for it: the setup prints `Left alone: <file>` on every run. A `phpstan.neon` the setup wrote earlier is removed (if unchanged) once you add one of your own, so it cannot shadow yours.
- The written file is owned like every setup file: a rerun reports `No changes`, and changing `phpstan_level` plans only that file. If you edit or replace it, the plan says `edited by hand: phpstan.neon` and `phpstan.neon: applying replaces your changes with level <n>`; nothing is written without your confirmation. To keep your own config, rename it to `phpstan.neon.dist` or `phpstan.dist.neon`: the setup then leaves it alone.
- With `phpstan/extension-installer` in `require` or `require-dev`, the file has no `includes` block: the installer already includes Larastan and this pack, and including them again makes PHPStan fail with "included multiple times". Adding or removing the installer later plans that change to `phpstan.neon` like any other refresh.

## CI workflow

With `"laravel": {"ci": true}` the setup writes `.github/workflows/claude-skills-gate.yml`, for an application or a Testbench package, whatever the runner. The workflow runs the same gate command as your machine, `composer test` (the script the setup writes), after `composer install`, on every push to the default branch and on every pull request, with read-only repository permissions. The default branch is the one origin's HEAD points to, else git's `init.defaultBranch`, else `main` (also `main` outside a git repository). A newer run cancels an older one for the same pull request; runs on the default branch always finish. It never runs Pint, PHPStan or the test runner on its own: the gate is the one command.

It also installs gitleaks (checksum verified), which the secret scan of `composer test` needs in CI, and, for an application whose suite runs on MySQL, MariaDB or PostgreSQL, starts a database service with the test database. The PHP version is the first of: `php_version` in `.ddev/config.yaml` (and its `config.*.yaml` overrides), `config.platform.php` in `composer.json`, the lowest version `require.php` allows, else 8.4. Each is reduced to X.Y.

The setup owns the file like every file it writes: the plan shows it as a diff, a copy you changed is reported as `edited by hand: .github/workflows/claude-skills-gate.yml` and is only replaced after you confirm.

## Rerun: only the difference

The profile is meant to be updated by a tool and the setup rerun to keep a repository current. A rerun applies only the difference:

- Changing one option plans only what follows from it: `ci` plans only the workflow; `phpstan_level` plans only `phpstan.neon`; `runner` plans only the runner-dependent files; `house_style` and `gate_tests` plan nothing.
- Rewriting the profile with the same meaning (keys reordered, other formatting, `managed_by` added) plans nothing.
- A rerun on an unchanged project reports `No changes` and `claude-skills:setup --check` exits 0.
