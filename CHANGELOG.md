# Changelog

All notable changes to this package are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package uses [Semantic Versioning](https://semver.org/). The first release will be `1.0.0-beta.1`; until then everything is listed under Unreleased.

## [Unreleased]

### Added

- `laravel-pitfalls` skill: pitfalls taken from real reviews (concurrency, transactions, idempotency, authorization, population, personal data in logs, edge validation, docs claims), each with its fix, its test and a note on what Boost already covers.
- PHPStan rules for those pitfalls, shipped as `extension.neon`.
- `laravel-package-verdicts` skill: a register of verdicts on common Laravel packages (use, avoid or depends), which a project profile can override.
- House PHP style guideline (strict types, PHPDocs on every class and method, `@author`, section headers), on by default and switched off with `"laravel": {"house_style": false}`.
- Project files guideline: README, docs, CHANGELOG and LICENSE ship where they apply and are updated in every slice that changes behavior, without waiting to be asked; it wins over Boost's "only create documentation files if explicitly requested".
- `claude-skills:setup` command for apps and Testbench packages: the runner (DDEV or host) for `.mcp.json` and the guidelines, an isolated test suite (forced PHPUnit pins, a `<slug>_test` database with a DDEV hook), the one gate command `composer test`, the commit-msg hook and secret scan, and `phpstan.neon` at the profile's level.
- The project profile `.ai/skills-profile.json`: runner, house style, PHPStan level, monitoring, the CI workflow, extra setup steps, package verdicts and outside builders. A value with a trailing newline is refused; `"laravel": []` counts as no options.
- `laravel.test_database: ddev`: a Testbench package on DDEV tests on DDEV's db service, as an app does (hook, credentials, pins and a CI database service on the same engine and version). With no `database:` block in `.ddev/config.yaml`, or one without a version, the engine and version come from the installed DDEV (`ddev describe -j`, `DDEV_DATABASE`, or the default `ddev config --help` prints); when DDEV cannot tell, the setup asks for an explicit block. DB keys you set in your own DDEV `web_environment` are left to you.
- `laravel.test_pins`: override single PHPUnit pins (`SESSION_DRIVER`, `CACHE_STORE`, `QUEUE_CONNECTION`, `MAIL_MAILER`) with a value or `env`; isolation stays the default.
- `laravel.php_matrix`: the CI workflow tests a list of PHP versions; a package defaults to every minor from its `require.php` floor to the latest.
- The setup creates an empty `CLAUDE.md` before Boost runs (so Boost never writes `AGENTS.md` instead) and, for a Pest package whose tests pick no base case yet, `tests/Pest.php`; it never touches either once it exists, and refuses a symlinked `tests` folder or a `CLAUDE.md` that links outside the project.
- Agents as a Claude Code plugin: planner, gate writer, builder, review checker, reviewer, deep reviewer and debugger, with locked gate tests, lock checks, revert-to-prove and an independent checker.
- `scripts/check.sh`: the package's deterministic quality gate.
- The setup lists every effective option with its source (`profile` or `default`) on every run, prints the two commands that install the agents plugin until it is enabled, and ends a plan with `<N> changes planned.`
- A package's `phpstan.neon` checks the existing `src`, `tests` and `workbench/app` directories, so a fresh package passes its own gate.
- The gate writer formats its own test files before the gate commit and reports every public name it chose under Open; the builder lists its steps without a todo tool, pushes and opens a PR only when the brief asks, stops a tripwire check after one test row per bypass, updates the README and CHANGELOG for its slice, and a gated PR merges with a merge commit, never a squash.
- The README documents the install order per project kind, requiring the unreleased pack from GitHub, the non-interactive Boost recipe and `boost:update` after a DDEV PHP change.
- Agents: a defect an agent finds is fixed in the slice or raised with the owner, never deferred, and every hand-back or report carries a `Learnings:` line (gaps in the agent or skill rules, stack learnings with evidence, or none). The gate writer works only from the pasted brief, stops on unstated values, and hands back `Values chosen:`, `Green by design:`, `Passability:`, `Constraints:`, `Breaks later:` and `Suite:`; the builder uses general-purpose stand-ins for a missing checker or gate writer type, reads vendor source when Boost's tools are missing, commits without attribution, watches CI after a push and proves new files and several fixes per file by mutation; the reviewers quote `|` filters, treat any vendor package source as evidence, check auth flows and give a `Merge:` result line, blocked on any Critical or Important finding or an unmet MUST; the planner fixes each slice's public names. A README describes behavior and never cites tests; docblocks and code comments name the test that proves a claim.
