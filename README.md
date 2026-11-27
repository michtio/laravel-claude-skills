# Laravel Claude Skills

Skills, agents and checks for Laravel projects, on top of [Laravel Boost](https://laravel.com/docs/boost).

Boost already ships Laravel best practices, first-party package skills and version-aware documentation search. This package adds only what Boost does not: pitfalls taken from real reviews, mechanical checks for them, a project setup step, and agents with independent gates.

Work in progress. Nothing is released yet.

The project setup (`claude-skills:setup`) reads an optional profile, `.ai/skills-profile.json`: see [docs/profile.md](docs/profile.md).

## Agents

The Claude Code plugin (`.claude-plugin/plugin.json`, from this repository's root) carries the agents. Skills ship through Boost, not through the plugin: install the Composer package and run `boost:install` so the agents find `laravel-pitfalls` and `laravel-package-verdicts` in `.claude/skills/`.

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

Read-only agents never get Boost's `tinker` or `record-rule` tools; the agents use Boost's read-only tools (`search-docs`, `database-schema`, `last-error`, `read-log-entries`) where they replace guessing. `python3 scripts/agent_budget.py` checks each agent's startup budget, agent cap and tool rules: planners, reviewers, checkers and the gate writer start no agents, except `laravel-reviewer-deep`, which orchestrates its checkers under its `At most 5 agents per review` line.
