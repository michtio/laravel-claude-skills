# Gate contract, slice S8 (laravel-layer)

Requirements: R7, R14, R15, R17, R22, R25. Acceptance criteria: AC8, AC17, AC19, AC21, AC23, AC24, AC25. Architecture: AD3, AD8, AD10, AD12 in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`. Gate discipline: rules G1 to G10 in the team's stack-neutral gate-discipline reference, which is kept outside this repo; this pack carries its own complete copy of the rules its agents own.

The gate is written before the builder starts. The builder writes the four agent files and the plugin.json entries to this contract and never edits `tests/gate/`, `tests/Agents/`, `evals/behavior-sets/agents.json` or `evals/fixtures/`. A change to the gate goes back to the gate writer.

Run from the repo root:

```
python3 -m unittest discover -s tests/gate     # includes tests/gate/test_s8.py; no DDEV, no network
sh scripts/check.sh                            # the package quality gate (must stay green)
ddev exec vendor/bin/pest                      # the PHP tier (must stay green)
```

## 1. What is proven now, and what only at S11

No release runner exists in this repo yet: `evals/release_evals.py`, `evals/facts_check.py` and `evals/behavior_check.py` are built in slice S11. So the S8 gate is split.

| Part | When it is proven | By |
|---|---|---|
| Agent files exist, are listed in plugin.json, pin model and effort | now | `test_s8.py` AgentFiles, Frontmatter |
| Budgets, caps, tool rules (AC19, AC25) | now | `scripts/agent_budget.py` on the real files, `test_s8.py` Budgets, `check.sh` |
| Facts pins: the text each case depends on is in the agent files | now | `test_s8.py` ReleaseCaseSchema (same semantics as the Craft pack's `facts_check.py`) |
| Content rules each agent must state (section 3) | now | `test_s8.py` ContentRules |
| Comparison with the gate-discipline rules (G1, G2, G3, G6, G8) | now | `test_s8.py` PackCheck |
| Release-case definitions: schema, assertions accept a good hand-back and reject each planted bad one, fixture apps behave as described | now | `test_s8.py` ReleaseCaseSchema, ReleaseCaseAssertions, FixtureApps |
| What a model actually does when it runs an agent | S11 only | the release runner over `evals/behavior-sets/agents.json` |

By acceptance criterion:

| AC | Proven now | Proven only at S11 (release case) |
|---|---|---|
| AC19 | fully: the budget check fails on a checker or gate writer with Agent and on a missing cap line, and passes on the real agents | none |
| AC25 | fully: no reviewer or checker lists tinker, all disallow it | none |
| AC21 | the gate writer's text states the commit message, `tests/` only, red with reasons, the builder's text starts the gate writer first | `builder-locked-flow` |
| AC8 | the builder states the revert-to-prove line and G8 | `builder-locked-flow` |
| AC23 | both agents state the 3-round cap, the builder hands back open findings | `builder-round-cap` |
| AC24 | the builder states the exact flow line and what isolation means | `builder-no-isolation` |
| AC17 | the planner states the cite form and the ruling ask | `planner-avoid-verdict` |

A line in `plan.md` claims more than this gate proves: S8's Verification gate says the three release cases pass (`builder-locked-flow` passes AC21, AC23 and AC8; `planner-avoid-verdict` passes AC17; `builder-no-isolation` passes AC24). That is true only once S11's runner exists. Until then S8 is done when the deterministic part passes; the release cases run at S11, or earlier by hand with `claude -p` (see section 4).

## 2. Files

| File | Notes |
|---|---|
| `agents/laravel-planner.md` | new |
| `agents/laravel-gate-writer.md` | new |
| `agents/laravel-builder.md` | new |
| `agents/laravel-review-checker.md` | replaces the S1 stub |
| `.claude-plugin/plugin.json` | `agents` lists every file in `agents/` as `./agents/<stem>.md` and nothing else; each entry exists |

Frontmatter keys, per agent:

| Agent | `name` | `model` | `effort` | `tools:` | `disallowedTools:` | Cap line |
|---|---|---|---|---|---|---|
| planner | `laravel-planner` | `opus` | `high` | none (inherits Boost's tools) | `Write, Edit, NotebookEdit, Agent, mcp__laravel-boost__tinker, mcp__laravel-boost__record-rule` | none (cap 0) |
| gate writer | `laravel-gate-writer` | `sonnet` | `high` | none | `Agent, mcp__laravel-boost__tinker, mcp__laravel-boost__record-rule`; never Write, Edit or Bash (it writes and runs tests) | none (cap 0) |
| builder | `laravel-builder` | `opus` | `high` | none, or a list that includes `Agent, Write, Edit, Bash, Skill` | none of `Agent, Task, Write, Edit, Bash` | `At most 4 agents per run` (the gate writer, the checker, two re-checks) |
| review checker | `laravel-review-checker` | `sonnet` | `high` | none | `Write, Edit, NotebookEdit, Agent, mcp__laravel-boost__tinker, mcp__laravel-boost__record-rule` | none (cap 0) |

`description` is set (more than 40 characters) and `name` equals the file stem. `effort` is `high`, never `xhigh`. No agent names a Boost tool in a `tools:` allowlist (AD3). A `skills:` preload is allowed (the S1 spike showed it works) but is not required; every preloaded name must exist under `resources/boost/skills/`. An agent that does not preload a skill loads it with the Skill tool. The checker file stays at most 16 KB, every agent at most 48 KB with preloads. No agent file names an outside model or tool (`qwen`, `mistral`, `ollama`, `gemini`, `glm`, `vibe`): the package says "local AI".

## 3. Required statements

Each statement is checked by a regex in `tests/gate/test_s8.py` (`CONTENT`); the text may say more. Where a rule has a Craft-pack wording that the team's pack comparison matches, the wording is fixed (marked PC).

### laravel-planner

- Consults `laravel-package-verdicts` and the profile at `.ai/skills-profile.json` before proposing a package (R14).
- Cites a verdict as `<package>: <use> (<reason>)` and, for `avoid`, asks for a ruling instead of adopting it (AC17).
- Plans in vertical slices; each slice names its R ids and a `Verification gate`; says the slice's gate tests are written by a separate gate writer.
- Read-only: returns the plan, writes nothing.
- Uses Boost's `search-docs` and `database-schema` where they replace guessing (R25); commands run through `ddev`.

### laravel-gate-writer

- PC G1: `A separate builder implements the slice` (afterwards, and may not change the tests).
- PC G2: `git commit -m "test(gate): <slice id>"`, and never stages anything outside `tests/` (AC21). Writes only under `tests/`.
- Each test is red for the right reason; a test that is green before the code exists is rewritten (AC21).
- Hand-back: `Gate commit:` line, a table with the columns `| AC | test | red reason |`, `Manual` and `Open` lines.
- PC G6: `Stop after 3 rounds` of fixing one test that will not go red for the right reason.
- No `->skip()`, todo or only markers; tests run through `ddev`, never on the host.

### laravel-builder

- Refuses to start without an approved spec; ends with a per-R-id table.
- Flow lines (R22, AC24): `Gate flow: locked (<gate commit>)` and `Gate flow: builder-written (<reason>)`, with `(no isolated suite)` and `(no Agent tool)` as reasons. A repo is isolated when `phpunit.xml` pins `DB_DATABASE` with `force="true"`; the opt-out is `gate_tests` in `.ai/skills-profile.json`. The Craft pack's `Gate tests:` line in `CLAUDE.md` is not used (Boost regenerates `CLAUDE.md`).
- Locked flow: starts `laravel-gate-writer` before any implementation, with a brief of verbatim acceptance criteria and no design, nothing else. When the caller gives a gate commit it starts no second gate writer.
- PC G3, both forms: `git diff --quiet <gate commit> HEAD -- <gate files>` and `git diff --quiet <gate commit> -- <gate files>`, run and pasted before hand-back. The old form `git diff --quiet -- <gate files>` never appears. A gate test it believes is wrong is never changed: `do not change it. Stop at a passing gate`.
- PC G6 (AC23): `Stop after 3 rounds`, handing back the open findings; no text caps rounds at 4 or more.
- PC G8 and AC8: states that a test that `would still pass with the fix reverted` proves nothing, and the hand-back carries `Revert-to-prove: <test> red without the fix, green with it`. Builder-written tests `Fail first`.
- Checker gate (R15): a `## Checker gate` section starting `laravel-review-checker` with `Pass no \`model\``; hand-back line `Checker: ...`, and `Checker: not run (no Agent tool)` rather than silence. `At most 4 agents per run`. The sensitive paths for sizing the check include `DB::raw`, `whereRaw`, `{!! !!}`, `$guarded`, `withoutMiddleware`, policies and gates, signed URLs and webhooks.
- Consults `laravel-package-verdicts` and flags a package in `composer.json` that the register says to avoid (R14).
- Uses Boost's `search-docs`, `last-error` and `database-schema` (R25); DDEV only, never `php`, `composer` or `npm` on the host.

### laravel-review-checker

- Read-only; checks one lens; reads `git diff`.
- Findings as `[Critical|Important|Suggestion] path:line` with an `Evidence:` line; a Critical or Important finding needs evidence it read; `No findings for <lens>.` when empty.
- `## Challenge mode`: `upheld | refuted | unsure`; `Refute only with a citation` (R15).
- No longer a stub.

## 4. Release cases (`evals/behavior-sets/agents.json`)

The format mirrors the Craft pack's `evals/behavior-sets/*.json` so S11's runner can share code: `id`, `note`, `cwd`, `copy_cwd`, `overlay`, `tools`, `max_turns`, `timeout`, `runs` (1 to 3), `expect_agent` and `expect_agents`, `max_agents` (counts the agent under test itself), `prompt`, `must_match` (a list of groups, any alternative of a group satisfies it), `must_not_match`, `facts` (`file`, `contains`, `not_contains`, regexes matched with `re.M` against the whole file). Assertions run `re.I | re.S` against the answer. Two additions, which the S11 runner must implement:

- `acs`: the acceptance criteria the case covers (documentation, validated for shape).
- `forbid_agents`: the case fails when the run starts one of these agent types.

| Case | Covers | Runs | Fixture |
|---|---|---|---|
| `builder-locked-flow` | AC21, AC8 (gate commit first and `tests/` only, red with reasons, both lock-check forms, revert-to-prove line, no builder-written flow, no fourth round) | 1 | `evals/fixtures/builder/isolated-app` + overlay `greeting-spec` |
| `builder-round-cap` | AC23 (a gate test that only the CI environment can turn green stays red; the builder stops after 3 rounds, hands back the open finding, never fabricates the token, starts no gate writer) | 1 | `evals/fixtures/builder/round-cap-app` |
| `builder-no-isolation` | AC24 (hand-back opens with `Gate flow: builder-written (no isolated suite)`, no gate writer, no gate commit) | 1 | `evals/fixtures/builder/no-isolation-app` + overlay `greeting-spec` |
| `planner-avoid-verdict` | AC17 (cites `laravel/ui: avoid (...)`, asks for a ruling, does not install it) | 3 (read-only) | `evals/fixtures/planner/avoid-ui-scaffold` |

Differences from the plan's wording, decided by the gate writer: AC23 has its own case (`builder-round-cap`) because one run cannot be both a green slice and a stuck gate without a forcing fixture; the builder's whole-flow case keeps AC8 and AC21. The read-only planner case repeats 3 times; builder cases run once (the Craft rule that `facts_check.py` enforces).

The fixture apps carry a stand-in `vendor/bin/pest` (sh, no PHP, no database) that goes red or green from marker comments in the tests (`expect-file`, `expect-contains`, `expect-env`; see each fixture's `CLAUDE.md`). Each fixture links `.claude/skills` to `resources/boost/skills`, so the register and pitfalls skills resolve as they would after `boost:install`. A `copy_cwd` run copies the fixture (symlinks followed) into a throwaway git repository.

`evals/fixtures/release-samples/<case>/pass.md` is a hand-back that must satisfy the case; each `fail-*.md` is a planted bad one that must not. `test_s8.py` scores them with the Craft pack's semantics, so an edit that loosens an assertion turns the gate red.

## 5. Round 2 (`tests/gate/test_s8_round2.py`)

The review of the first build found gaps. Each statement below is behaviour a real agent must follow; the test checks that the agent's text carries it. What a model does with the text is S11's job.

### laravel-builder

- **R22, gate flow order.** The profile opt-out and the isolation check are decided before a caller-supplied gate commit. A caller commit only means "start no second gate writer". On a non-isolated suite the flow line is `Gate flow: builder-written (no isolated suite)`, followed by `Gate commit (supplied, not locked): <hash>`. Both lock checks are still run and pasted, and Open carries `suite not isolated: tests ran against the configured DB`. The builder stops before the first test run only when the tests use a database-wiping trait (`RefreshDatabase`, `DatabaseMigrations`, `DatabaseTruncation`, `LazilyRefreshDatabase`) on a non-isolated suite, and asks for the pin.
- **Isolation** also counts sqlite `:memory:` and Testbench's in-memory default as isolated.
- **G4, builder-wide.** The builder never skips, todos, onlys, deletes or loosens any existing test, and never edits test config (`tests/Pest.php`, `TestCase`, the `phpunit.xml` pins) to get green; it reports a red old test instead. The gate files come from `git show --name-only --format= <gate commit>`, never from a hand-back list.
- **Revert-to-prove safety.** After `git stash push -m "revert-to-prove <slice>"` the builder confirms an entry with that exact message exists and that the fix files actually reverted; if not it uses `git checkout <base> -- <files>`. On an apply conflict, or an error between push and apply, it stops and reports. It never ends a run with its fix in the stash.
- **Runner.** An explicit profile runner wins over detection; with no `.ddev/` and no named command it asks or stops.
- **Register.** A missing register is reported, and every package is then treated as having no verdict (planner too).
- **Mirrors the Craft builder:** a mandatory todo list when the plan has more than 3 steps, a simplification pass before the hand-back, "stop early at a passing gate and report the remainder", a Manual checks section and a `Reuse:` line.

### laravel-gate-writer

- **G2 staging.** Before committing, verifies that `git diff --cached --name-only` equals exactly its own files under `tests/`, or commits with `git commit -m "test(gate): <slice id>" -- <files>`; stops if anything else is staged.
- **Isolation.** Before its first run, checks for the forced `DB_DATABASE` pin (or an in-memory sqlite connection) and stops if it is missing.
- States that "No tests found" for an empty filter is not red for the right reason.

### laravel-planner and laravel-review-checker

- Deny every write-capable built-in tool that can be named (`Write`, `Edit`, `NotebookEdit`, `Agent`) plus tinker and record-rule, with no `tools:` allowlist, so Boost's tools stay reachable (AD3).
- State that Bash is limited by instruction only, and list the forbidden Bash classes: `migrate`, `db:wipe`, `composer require` and `composer remove`, file writes, `git commit`, `git push`, `git stash`.
- Checker only: the weakening list adds todo markers, deleted test blocks and changed gate-commit files to skips, onlys, fewer assertions and looser matchers.

## 6. Not covered here

- G4 and G5 (weakening list, gate reruns) and G7 (debugger hypotheses) belong to the reviewer and the debugger: slice S9. G9 and G10 are pending in the reference itself.
- The outside-builder path (AC26, AC28) is slice S10.
- The `claude-skills` setup and profile are S6 and S7.
