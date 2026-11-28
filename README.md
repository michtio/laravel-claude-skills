# Laravel Claude Skills

Skills, agents and checks for Laravel projects, on top of [Laravel Boost](https://laravel.com/docs/boost).

Boost already ships Laravel best practices, first-party package skills and version-aware documentation search. This package adds only what Boost does not: pitfalls taken from real reviews, mechanical checks for them, a project setup step, and agents with independent gates.

Work in progress. Nothing is released yet.

The project setup (`claude-skills:setup`) reads an optional profile, `.ai/skills-profile.json`: see [docs/profile.md](docs/profile.md).

## Install

The order matters, and it differs a little per project kind. Each kind runs the setup, then `boost:install`, then the setup again. Boost's `boost:install` leaves `.mcp.json` reset to its own host command (`php artisan boost:mcp`), so the second setup run puts the runner's command back; `--check` then confirms nothing is left to change. The setup also creates an empty `CLAUDE.md` when the project has none: Boost writes its guidelines to `AGENTS.md` when `CLAUDE.md` is missing, and Claude Code would then never read them. The setup never edits a `CLAUDE.md` that exists.

### Requiring the unreleased pack

Until the first tag (`1.0.0-beta.1`) the pack is not on Packagist. Require it from GitHub through a VCS repository in `composer.json`:

```json
{
    "repositories": [
        {"type": "vcs", "url": "https://github.com/michtio/laravel-claude-skills"}
    ],
    "require-dev": {
        "michtio/laravel-claude-skills": "dev-develop"
    }
}
```

`composer.lock` pins the exact commit, so every clone and CI install the same one; `composer update michtio/laravel-claude-skills` moves it to the latest `develop`. After the first release, require a version (`composer require --dev michtio/laravel-claude-skills`) and drop the repository block.

### Boost without prompts

`boost:install` asks with interactive prompts, which an agent shell cannot answer, and with `--no-interaction` on a first run it takes its choices from `boost.json`, which does not exist yet. The first setup run creates this `boost.json` when the project has none (and never changes one that exists), so Boost installs for Claude Code, includes this pack's skills and leaves the Laravel Cloud skill off:

```json
{"agents": ["claude_code"], "packages": ["michtio/laravel-claude-skills"], "cloud": false}
```

The steps below run `boost:install --guidelines --skills --mcp --no-interaction`, which needs that seed. To answer Boost's prompts yourself instead, drop the flags from that line.

### An app

On DDEV:

```sh
ddev composer require --dev michtio/laravel-claude-skills
ddev artisan claude-skills:setup
ddev artisan boost:install --guidelines --skills --mcp --no-interaction
ddev artisan claude-skills:setup
ddev artisan claude-skills:setup --check
```

On the host:

```sh
composer require --dev michtio/laravel-claude-skills
php artisan claude-skills:setup
php artisan boost:install --guidelines --skills --mcp --no-interaction
php artisan claude-skills:setup
php artisan claude-skills:setup --check
```

On a DDEV project whose type is not `laravel`, use `ddev exec php artisan` instead of `ddev artisan`.

### A Testbench package

A package has no `artisan`: every command goes through `vendor/bin/testbench`. The package kind needs a `workbench/` directory, and `workbench:install --basic --devtool` creates it (without `--devtool` it writes only `testbench.yaml`). The workbench it writes is not Pint-clean, so format it once with `pint workbench`.

```sh
ddev composer require --dev michtio/laravel-claude-skills
ddev exec php vendor/bin/testbench workbench:install --basic --devtool --no-interaction
ddev exec vendor/bin/pint workbench
ddev exec php vendor/bin/testbench claude-skills:setup
ddev exec php vendor/bin/testbench boost:install --guidelines --skills --mcp --no-interaction
ddev exec php vendor/bin/testbench claude-skills:setup
ddev exec php vendor/bin/testbench claude-skills:setup --check
```

On the host, drop `ddev exec` (and use `composer` for `ddev composer`). Run `boost:install` only after the first setup: before it, Testbench's `base_path()` is its own `@testbench` skeleton in `vendor/`, and Boost writes its files there instead of into the package. The setup warns when it finds Boost's files there.

Boost decides whether its guidelines enforce tests with `config('boost.enforce_tests')`, else by running `artisan test --list-tests`, which a package has no `artisan` for, so enforcement stays off in a package. To switch it on, set `config(['boost.enforce_tests' => true]);` in the `register()` method of a provider Testbench loads (the workbench's `WorkbenchServiceProvider`, listed under `providers:` in `testbench.yaml`), then run `boost:install` again. The runner guideline tells agents to run a package's tests with `vendor/bin/pest`, to keep package classes under `src/`, and that `make:` generators write into the skeleton, not into `src/`.

### After the install

The agents ship as a Claude Code plugin, separately from the skills. In Claude Code, run:

```text
/plugin marketplace add michtio/laravel-claude-skills
/plugin install laravel-claude-skills@laravel-claude-skills
```

The setup prints these two commands on every run until the project's `.claude/settings.json` enables the plugin.

When the DDEV PHP version changes (`php_version` in `.ddev/config.yaml`), run `boost:update` (`ddev artisan boost:update`, or `ddev exec php vendor/bin/testbench boost:update` in a package): Boost's guidelines in `CLAUDE.md` keep naming the old PHP version until Boost composes them again. For an app with `"ci": true` and `"php_matrix": "auto"`, also rerun the setup: its CI workflow takes the PHP version from DDEV and refreshes it. A package matrix and a `php_matrix` list do not follow DDEV.

Every setup run also prints suggested `.claude/settings.json` permissions for the project; the setup never writes that file.

A gated pull request (one that carries a `test(gate):` gate commit) merges with a merge commit, never a squash: a squash rewrites the slice into one new commit and removes the gate commit that the lock check compares against, so the gate can no longer be proven untouched.

### Install with skills.sh

The skills alone (`laravel-pitfalls`, `laravel-package-verdicts` and `laravel-gated-build`) also install through [skills.sh](https://skills.sh), without Composer or Boost, for example in a project that does not run Boost or for another agent:

```sh
npx skills add michtio/laravel-claude-skills
```

Add `-a claude-code` to install for Claude Code only (into `.claude/skills/`), and `npx skills update` later to move them to the latest commit. This channel carries the skills and their references only: no guideline, no setup command, no PHPStan rules and no agents. In a Laravel project with Boost, prefer the Composer install above, which keeps the skills in step with the package version.

## Using it with Spatie's guidelines

[spatie/guidelines-skills](https://github.com/spatie/guidelines-skills) ships Spatie's code style for Laravel, PHP and JavaScript as Boost guidelines and skills. The two packages install side by side: their skill names do not overlap, and Boost keys each package's guideline by package name, so neither replaces the other. Spatie's PHP style contradicts this pack's house style (PHPDocs on every method, `@author`, `=========` section headers), so switch the house style off in `.ai/skills-profile.json`:

```json
{"version": 1, "laravel": {"house_style": false}}
```

With `"house_style": false` this pack keeps its pitfalls, package verdicts, runner guideline, project files rule and agents, and Spatie's guideline decides the code style. Then require Spatie's package, add `"spatie/guidelines-skills"` to `packages` in `boost.json` (for a non-interactive install), and run `boost:install` again (`ddev artisan boost:install --guidelines --skills --mcp --no-interaction` on DDEV) so Boost composes both.

## Agents

The Claude Code plugin (`.claude-plugin/plugin.json`, from this repository's root) carries the agents: add it with `/plugin marketplace add michtio/laravel-claude-skills` and `/plugin install laravel-claude-skills@laravel-claude-skills` (see [After the install](#after-the-install)). Skills ship through Boost, not through the plugin: install the Composer package and run `boost:install` in the order of [Install](#install), so the agents find `laravel-pitfalls` and `laravel-package-verdicts` in `.claude/skills/`.

| Agent | Model, effort | Starts | What it does |
|---|---|---|---|
| `laravel-planner` | opus, high | none | Turns an approved PRD into `plan.md`: vertical slices, each with its R ids and a runnable verification gate. Checks every package against the verdicts register and asks for a ruling on any it says to avoid. Read-only. |
| `laravel-gate-writer` | sonnet, high | none | Writes a slice's gate tests from its acceptance criteria alone, runs each red for the right reason, and commits them alone as `test(gate): <slice id>`, touching only `tests/`. Started by the builder. |
| `laravel-builder` | opus, high | at most 4 | Builds one approved slice. In the locked gate flow it starts the gate writer first, never edits the gate tests and proves it with two `git diff --quiet` checks against the gate commit; it stops after 3 fix rounds, proves each fix by reverting it, and runs an independent checker before it hands back. |
| `laravel-review-checker` | sonnet, high | none | Checks one lens of a diff (security, conventions) with evidence it read, and challenges other findings, refuting only with a citation. Read-only. |
| `laravel-reviewer` | sonnet, high | none | Everyday review of a diff, untracked files included. Flags every test weakening (skip, todo and only markers, deleted or commented-out tests, fewer assertions, loosened matchers, narrowed datasets, edits to gate-commit files or test configuration) as Important or higher, runs both lock checks against the gate commit, and reruns the builder's gate commands only on an isolated suite, else reports `claimed, not rerun (<reason>)`. Read-only. |
| `laravel-reviewer-deep` | opus, high | at most 5 | Deep review for release branches and high-stakes changes. Runs the project's static checks once (Larastan, Pint in test mode, the architecture tests) and ranks findings they back above opinions, tagged `[larastan]`, `[pint]` or `[arch]`; flags packages the register says to avoid; starts lens checkers (always conventions and security, the security lens on Opus) and one fresh challenger. A small diff in one area gets a single pass. Read-only. |
| `laravel-debugger` | sonnet, high | none | Reproduces first, writes 2 or 3 hypotheses each with one deciding check before reading code, proves the bug with a regression test that is red for the right reason before the smallest root-cause fix, and stops after 3 rounds. Hands back each root cause with file:line and a `hypothesis \| check \| result \| kept/rejected` table. Never bends a test to get green. |

The locked gate flow needs an isolated suite: `phpunit.xml` pins the test database with `<env name="DB_DATABASE" ... force="true"/>` (the setup writes it). Without one, or when the profile sets `"gate_tests": "builder-written"`, the builder writes its own tests, each failing first, and its hand-back opens with `Gate flow: builder-written (<reason>)`.

A defect an agent finds is fixed in the slice (a finding, for the read-only agents), unless the fix needs a ruling (a spec change, the public API, or scope); then it is raised with the owner. It is never marked later, out of scope or for a follow-up.

Every hand-back and report ends with a `Learnings:` line in two kinds, gaps in the agent or skill rules and stack learnings with evidence, or `none`.

Read-only agents never get Boost's `tinker` or `record-rule` tools; the agents use Boost's read-only tools (`search-docs`, `database-schema`, `last-error`, `read-log-entries`) where they replace guessing. `python3 scripts/agent_budget.py` checks each agent's startup budget, agent cap and tool rules: planners, reviewers, checkers and the gate writer start no agents, except `laravel-reviewer-deep`, which orchestrates its checkers under its `At most 5 agents per review` line.

## Outside builders

A slice can also be built by a program other than `laravel-builder`: a local AI, a script or a team tool. Name them under `builders` in `.ai/skills-profile.json` and ask Claude Code to build the slice with the `laravel-gated-build` skill. The gate writer still commits the gate first; each builder, in the profile's order, is called as `<command> <brief-file> <handback-file>`, gets the same brief and writes a hand-back; both lock checks, the hand-back check (`scripts/handback_check.py`), your own gate run and `laravel-review-checker` cover its result, with at most 3 rounds per builder. A builder that exits 3 (unavailable), fails or outlives its `timeout_minutes` hands over to the next one, and `laravel-builder` builds the slice from the same brief when none of them succeeds. The build never stops silently: the report names every builder tried and how it ended.

The commands come from the repository, so the gated build prints each one as `<name>: <command> (timeout <n> min)` and runs none of them until you say yes to that list; a request that names every command exactly counts as the yes. Your yes is kept once per machine, outside the repository (`~/.config/laravel-claude-skills/trusted-builders.json`): a builder you confirmed is marked `(trusted)` and runs without asking, unattended runs included, until its name, command, timeout or the repository file it runs changes (a task runner such as `make` is marked `(runs repo code)`); `scripts/builder_trust.py remove --root <project root> --name <name>` revokes it, and a trust file inside the project is ignored. Without a yes, or in an unattended run, a builder that is not trusted is skipped with `Skipped: <name> (not confirmed)`, and `laravel-builder` builds the slice when none is left. A builder whose name is not plain letters, digits, `.`, `_` and `-` (at most 64), or whose command holds a Unicode control, format or separator character, is skipped and reported. A builder that changes the test configuration (`phpunit.xml`, `phpunit.xml.dist`, `tests/Pest.php`, `tests/TestCase.php`, `.env`, `.env.testing`, `testbench.yaml`, `config/database.php` and the phpunit bootstrap file (unless it is under `vendor/`)) is disqualified before the gate runs on its code; a suite that is not isolated and wipes its database (a wiping trait, or `migrate:fresh`, `migrate:refresh`, `migrate:reset` or `db:wipe`) runs no builder at all, and a builder that adds such a test is disqualified.

The protocol is in [docs/outside-builders.md](docs/outside-builders.md) and the brief and hand-back formats in [docs/brief-format.md](docs/brief-format.md), written for any builder, not only Claude.
