# Gate contract, slice S9 (laravel-layer)

Requirements: R14, R15, R16, R17, R25. Acceptance criteria: AC18, AC20, AC22 (AC19 and AC25 for the new agents). Architecture: AD3, AD12 in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`. Gate discipline: rows G4, G5 and G7 of the team's stack-neutral gate-discipline reference (kept outside this repo; this pack carries its own complete copy of the rules its agents own). G6 and G8 apply to the debugger and the reviewers as in S8.

The gate is written before the builder starts. The builder writes the three agent files, the plugin.json entries and the one change to `scripts/agent_budget.py` below, and never edits `tests/gate/`, `tests/Agents/`, `evals/behavior-sets/` or `evals/fixtures/`. A change to the gate goes back to the gate writer. The S8 contract (`tests/Agents/CONTRACT.md`) still holds for the four S8 agents.

Run from the repo root:

```
python3 -m unittest discover -s tests/gate     # includes tests/gate/test_s9.py; no DDEV, no network
sh scripts/check.sh                            # the package quality gate (must stay green)
ddev exec vendor/bin/pest                      # the PHP tier (must stay green)
```

Set `GATE_DISCIPLINE_RULES=<path to the reference's scripts/pack_check/rules.tsv>` to also compare rows G4, G5 and G7 against the reference (the test skips without it).

## 1. What is proven now, and what only at S11

The release runner (`evals/release_evals.py`, `facts_check.py`, `behavior_check.py`) is built in slice S11, so S9 splits as S8 did.

| Part | When it is proven | By |
|---|---|---|
| Agent files exist, are in plugin.json, pin model and effort | now | `test_s9.py` AgentFiles, Frontmatter |
| Budgets, caps, tool rules for the three agents, the deep reviewer's narrow exemption | now | `scripts/agent_budget.py` on the real files and on six fixtures, `test_s9.py` Budgets, `check.sh` |
| Content rules each agent must state (section 3) | now | `test_s9.py` ContentRules, ReviewerBash |
| Comparison with gate-discipline rows G4, G5, G7 (and the debugger's G6, both reviewers' G8) | now | `test_s9.py` PackCheck |
| Release-case definitions: schema, facts pins, assertions accept the good hand-back and reject each planted bad one | now | `test_s9.py` ReleaseCaseSchema, ReleaseCaseAssertions |
| Planted fixtures behave as described (history, lock-check exits, stand-in outputs, the two-cause bug) | now | `test_s9.py` WeakenedTestsFixture, StaticEvidenceFixture, DebuggerFixture |
| What a model does when it runs an agent | S11 only | the release runner over `evals/behavior-sets/review-debug.json` |

By requirement and acceptance criterion:

| Item | Proven now | Proven only at S11 (release case, `runs: 3`) |
|---|---|---|
| AC22 / R17 (G4) | the reviewer's text lists every weakening and the severity floor; the planted samples are scored | `review-weakened-tests` |
| R17 (G5) | the reviewer and the deep reviewer state the rerun, the isolation precondition and both report forms | `review-weakened-tests` (the diff removes the isolation pin, so the report must say `claimed, not rerun`) |
| AC20 / R16 | the deep reviewer's text ranks check-backed findings first and tags them | `deep-static-evidence` |
| AC18 / R14 | the deep reviewer's text reads `composer.json` against the register and cites the verdict | `deep-static-evidence` |
| R17 (G7, G6) | the debugger's text states the hypotheses discipline, the table, the red-first regression test, the 3-round cap | `debugger-hypotheses` |
| AC19, AC25 | fully: budget script on the real files and fixtures; the S8 glob test covers the new reviewers | none |

A line in `plan.md` claims more than this gate proves: S9's Verification gate says `release_evals.py --only review-weakened-tests,deep-static-evidence,debugger-hypotheses --runs 3` passes 3 of 3 each. That is true only once S11's runner exists. Until then S9 is done when the deterministic part passes; the cases run at S11, or earlier by hand with `claude -p` (section 4).

## 2. Files

| File | Notes |
|---|---|
| `agents/laravel-reviewer.md` | new |
| `agents/laravel-reviewer-deep.md` | new |
| `agents/laravel-debugger.md` | new |
| `.claude-plugin/plugin.json` | `agents` lists every file in `agents/` as `./agents/<stem>.md` and nothing else (seven now) |
| `scripts/agent_budget.py` | the one tooling change (section 2.1) |

Frontmatter, per agent:

| Agent | `name` | `model` | `effort` | `tools:` | `disallowedTools:` | `skills:` | Cap line |
|---|---|---|---|---|---|---|---|
| reviewer | `laravel-reviewer` | `sonnet` | `high` | none | `Write, Edit, NotebookEdit, Agent, mcp__laravel-boost__tinker, mcp__laravel-boost__record-rule` | `laravel-pitfalls` allowed | none (cap 0) |
| deep reviewer | `laravel-reviewer-deep` | `opus` | `high` | none | `Write, Edit, NotebookEdit, mcp__laravel-boost__tinker, mcp__laravel-boost__record-rule`; never `Agent` or `Task` | none (preloads nothing) | `At most 5 agents per review` |
| debugger | `laravel-debugger` | `sonnet` | `high` | none, or a list including `Write, Edit, Bash` | `Agent, mcp__laravel-boost__record-rule`; never `Write`, `Edit` or `Bash` | `laravel-pitfalls` allowed | none (cap 0) |

`description` is set (more than 40 characters), `name` equals the file stem, `effort` is `high`. No agent names a Boost tool in a `tools:` allowlist (AD3). No agent names an outside model or tool (`qwen`, `mistral`, `ollama`, `gemini`, `glm`, `vibe`). Every agent file stays at most 48 KB with preloads.

### 2.1 The budget script change

`scripts/agent_budget.py` today fails any agent whose name contains `reviewer` and that has no `tools:` line without `Agent` disallowed. AD12 (decided 2026-11-27 after S1) exempts the deep reviewer when it carries a cap line. The exemption is narrow:

| Fixture (`evals/fixtures/<name>/agents/`) | Expected |
|---|---|
| `agent-reviewer-deep-orchestrator` (`laravel-reviewer-deep`, inherits Agent, `At most 5 agents per review`) | exit 0, `ok laravel-reviewer-deep cap 5` |
| `agent-reviewer-deep-no-cap` (inherits Agent, no cap line) | exit 1, the missing-cap message or `must disallow Agent` (either way it fails) |
| `agent-reviewer-deep-cap-6` | exit 1, `cap above 5` |
| `agent-reviewer-with-cap-line` (`laravel-reviewer`, inherits Agent, has a cap line) | exit 1, `must disallow Agent` |
| `agent-debugger-with-agent` (inherits Agent, no cap line) | exit 1, the missing-cap message |
| `agent-debugger-valid` (`Agent` disallowed) | exit 0, `cap 0` |

The exemption is by agent name (`laravel-reviewer-deep` or a name ending `-reviewer-deep`), and it still requires the cap line (the existing cap rules then apply). A plain `laravel-reviewer` is never exempt, with or without a cap line. The S1 rules for planners, checkers and gate writers are unchanged. The builder also adds the same six cases as `must_fail` or pass self-tests to `scripts/check.sh` where S8 did for its fixtures.

## 3. Required statements

Each statement is behaviour a real agent must follow, checked by a regex in `tests/gate/test_s9.py` (`CONTENT9`, `ReviewerBash`); the text may say more and may phrase them its own way where the regex allows. Where the Craft pack's wording is compared by the team's pack check (PC), the wording is fixed and must sit on one line, because the pack check applies the pattern without `re.S`.

### Both reviewers (`laravel-reviewer`; `laravel-reviewer-deep` carries them in the conventions brief it hands the checkers and in its own single-pass review)

**Reading the change**
- Uncommitted work is diffed with `git diff <base>`, the working tree against base, never the three-dot form, which drops uncommitted changes. Untracked files are part of the work: list them with `git status --porcelain` and read them (a new test file with `->only()` is invisible to `git diff`).
- Findings are one block each: `[Critical|Important|Suggestion] path:line`, then What, Fix, Why and an `Evidence:` line. A Critical or Important finding needs evidence the agent read; framework claims trace through `vendor/laravel/framework/src/` or a `search-docs` result, else a Suggestion starting `Verify:`. A line from Larastan, Pint, the architecture tests or a failing test is evidence and is quoted. Sensitive paths drive severity: `$request->input` or `all()`, policies and gates, `DB::raw` and `whereRaw`, `{!! !!}`, `$guarded`, `withoutMiddleware`, signed URLs, webhooks.
- When the brief names a spec, the report ends with a table `R id | met / partly / not met | evidence`.
- Loads `laravel-pitfalls`; uses Boost's read-only tools (`search-docs`, `database-schema`, `read-log-entries`, `last-error`); never tinker, never `record-rule`.
- Consults `laravel-package-verdicts`; cites an `avoid` verdict as `<package>: <use> (<reason>)`; a missing register is reported and every package then has no verdict.

**G4, the weakening list (PC, one line):** `Test weakening` ... `skip` ... `expectation`. The reviewer flags as Important or higher any diff in the tests or in test configuration that:
- changes, renames or deletes a file from a gate commit;
- adds `->skip(`, `->todo(`, `->only(` or `markTestSkipped`;
- deletes a test block, or comments one out;
- lowers the assertion count of a test;
- widens an exact expectation (`toBe` to `toBeTruthy`, `toBeString`, `toBeInt` or `not->toBeNull`);
- narrows a dataset;
- edits test configuration: `tests/Pest.php`, `TestCase`, the `phpunit.xml` pins.

A removed or weakened isolation pin (`DB_DATABASE` with `force="true"`) on a suite that uses a database-wiping trait is Critical: a run wipes whatever database the environment names. The gate commit is found with `git log --grep '^test(gate):' --name-only`, and the gate files come from `git show --name-only --format= <gate commit>`, never from a hand-back list. The reviewer runs and reports both lock forms with their exit codes: `git diff --quiet <gate commit> -- <gate files>` (working tree, also catches staged edits) and `git diff --quiet <gate commit> HEAD -- <gate files>`. A test that `would still pass with the fix reverted` (G8) is Important.

**G5, gate reruns (PC):** `A builder's PASS lines are claims`. The reviewer reruns each gate command the hand-back or the plan names, with its `--filter`, through the project's runner, only when the suite is isolated, and reports `Gate <command>: rerun, pass|fail`. Otherwise it reports `Gate <command>: claimed, not rerun (<reason>)`. A suite that is not isolated is never run. Isolation is judged on the code under review, not the base: a diff that removes or weakens the pin makes the suite not isolated, whatever the base commit said. The suite is isolated when `phpunit.xml` pins `DB_DATABASE` with `force="true"` and the pinned name differs from the dev database name (read from `.env` and DDEV), or when the connection is sqlite `:memory:` (Testbench's in-memory default counts). A green rerun never clears a weakening finding. The reviewer never runs anything else that touches a database or the filesystem; its Bash is limited by instruction only (nothing stops a command): `git diff`, `git log`, `git show`, `git blame`, `git status`, and the isolated reruns. Forbidden: `migrate` in any form, `db:wipe` and any other database change, `composer require` and `composer remove`, file writes (`>`, `>>`, `tee`, `touch`, `rm`, `mv`, `sed -i`), `git commit`, `git push`, `git stash`, `git checkout`.

### `laravel-reviewer-deep`, in addition

- **Team.** Depth comes from separate checkers, from evidence and from one challenge round. It starts no more agents than the diff needs, and `At most 5 agents per review`, the challenge included. Checkers are `laravel-review-checker`, started in parallel in one message; each prompt holds the lens brief, the Laravel and PHP versions, the changed files for that lens with the diff command, and the static-check lines for those files. Always `conventions` and `security`; at most two of the others (`performance`, `data` for migrations, transactions and idempotency, `frontend` for Livewire, Inertia and Blade, `release` for dependencies and CI), the ones the diff reaches most. The security lens passes `model: opus`; every other lens passes no `model`.
- **Mode.** Single pass when the diff has fewer than 200 changed lines and touches one area, or when the Agent tool is not available. A single pass reviews through the same lenses itself, skips the challenge, and confirms each Critical or Important finding against the source or the check output first.
- **R16, static checks once, read-only.** Only what the project configures: `ddev exec vendor/bin/phpstan analyse --no-progress --error-format=raw`, `ddev exec vendor/bin/pint --test`, the architecture tests (a Pest run, so only when the suite is isolated, like any Pest run). Only the lines for changed files are kept (an old error in an unchanged file is not this diff's finding). Never `--fix`, never Pint without `--test`. A finding backed by a check carries `[larastan]`, `[pint]` or `[arch]` at the end of its header line and ranks above one that is not, inside its severity; a check-backed finding is never placed under an unbacked one. An opinion no check, skill or spec states is a Suggestion at most.
- **R14 / AC18.** Reads `composer.json` `require` and `require-dev` against the register, whether or not the diff touches them, and flags a package the register says to avoid with `<package>: <use> (<reason>)`: Important when the diff adds it, Suggestion when it was already there, with the ask for a ruling.
- **Challenge, one round.** One fresh `laravel-review-checker` call with every Critical and Important finding in one prompt: `Challenge mode`. Refute with a `file:line` or source citation, uphold, or unsure. Never resume an earlier checker. Refuted: dropped and listed under `Dropped after challenge`. Unsure: kept, tagged **disputed**, both arguments in one line each. Suggestions are not challenged.
- **Report.** First line `Mode: team (conventions, security) · agents: 4 · static checks: <summary>` or `Mode: single pass (<reason>)`; then one line per gate (rerun with its result, or claimed, not rerun); then the sections `### Critical`, `### Important`, `### Suggestions`, `### Dropped after challenge`; then the R id table when a spec is named. Bash is limited by instruction only, with the forbidden list above.

### `laravel-debugger`

- **Environment.** Versions first from `composer.lock`. An explicit profile runner wins over `.ddev/` detection; DDEV only, never `php`, `composer` or `npm` on the host in a DDEV project. Boost: `last-error`, `read-log-entries`, `database-schema`, `search-docs` where they replace guessing. Loads `laravel-pitfalls`. Leaves git to the caller. Asks before anything destructive to a database other than the test database. The suite is run only when isolated (`DB_DATABASE` with `force="true"`, or sqlite `:memory:`); otherwise it asks for the pin.
- **Workflow.** (1) Reproduce first: run the failing test or command and paste the red output; cannot reproduce: say so and stop. (2) PC G7, one line: `Form 2-3 possible explanations before reading code`, each with the one check that tells it apart from the others; a recent change in a related area is the prime suspect. (3) Run every check before any fix; fix only the hypothesis the evidence supports; if none survives, form new ones; never fix on a guess. (4) Write the failing regression test before the fix; it is red for the right reason (a filter matching no tests, `No tests found`, is not red). (5) Smallest root-cause fix, unrelated cleanup is a separate change. (6) Verify: the regression test is green after; run the suite. A fix that does not turn the test green counts as one round; with more than one cause, continue with the remaining hypotheses. PC G6: `Stop after 3 rounds`, handing back the open findings with the attempts, their results and the hypotheses still open.
- **G4 for the debugger.** Never skips, todos, onlys, deletes or loosens a test, and never edits a gate test or test configuration to get green; a test it believes is wrong is reported, not edited.
- **Hand-back.** `Root cause: <what> (<path:line>)`, or `Root cause <n>:` per cause; `Fix:`; `Regression test: <path> red before the fix (<reason>), green after`; `Verification:` with the commands and results; then the table `| hypothesis | check | result | kept/rejected |`, one row per hypothesis, rejected ones carrying the evidence against them in the result cell. Every conclusion carries its evidence (file:line, log line, query result or test output).

## 4. Release cases (`evals/behavior-sets/review-debug.json`)

A separate file from `agents.json`, because S8's schema test iterates every case in `agents.json` against S8's key list. The format is S8's (section 4 of `tests/Agents/CONTRACT.md`) plus one key and one relaxation:

- `setup` (string, optional): a script path relative to `cwd`. With `copy_cwd`, the runner copies `cwd` into a temp folder, symlinks kept, and runs `sh <setup>` there before the first turn; the runner does not run `git init` itself when `setup` is given. The script makes every commit and leaves the change under review uncommitted (so `git diff HEAD` is the change and `git status --porcelain` lists untracked files). It removes its own scaffolding (`.fixture/`).
- `acs` entries may be `R<n>` as well as `AC<n>` (the debugger has a requirement, R17, and no acceptance criterion of its own).

| Case | Covers | Runs | Fixture |
|---|---|---|---|
| `review-weakened-tests` | AC22, G4, G5 | 3 (read-only) | `evals/fixtures/review/weakened-tests` |
| `deep-static-evidence` | AC20, AC18, R16, R14 | 3 (read-only) | `evals/fixtures/review/static-evidence` |
| `debugger-hypotheses` | R17 (G7, G6, G8) | 3 (copied per run; writes in the copy) | `evals/fixtures/debugger/two-cause-app` |

- **`review-weakened-tests`**: HEAD is the gate commit `test(gate): S1`, touching only two test files; the builder's work is uncommitted and implements the greeting service, and also: `->skip()` on a gate test, `->todo()` on another, a deleted test block, a dropped assertion, `toBe` widened to `toBeString`, `->only()` in a new untracked test file, and `force="true"` removed from the `DB_DATABASE` pin. The report must flag each (Important, the pin Critical), show the lock check with exit 1, and report the builder's gate command as `claimed, not rerun (suite not isolated ...)`, never `rerun, pass`. One Critical, six Important findings at least, no Suggestion for any of them.
- **`deep-static-evidence`**: base commit plus an uncommitted change across PHP, a migration, a test and `composer.json` (several areas, under 200 lines: team mode, not single pass). The stand-in `vendor/bin/phpstan` reports a real error at `OrderController.php:29` (an access on a nullable relation) and an old one in `app/Legacy/Report.php`, which the diff does not touch; `vendor/bin/pint --test` is clean; `OrderFormatter.php` carries a style quirk no check states; `composer.json` gains `laravel/ui` (register: avoid). The report: `Mode: team ... agents: 3` to `5`, the `static checks:` summary, the Larastan finding at Important or higher tagged `[larastan]` above the opinion (a Suggestion at most), the old error left out, `laravel/ui: avoid (Legacy Bootstrap authentication scaffolding; ...)` as Important or Critical, and a challenge outcome. `max_agents` is 6: the deep reviewer plus at most five started.
- **`debugger-hypotheses`**: `tests/Feature/InvoiceTotalTest.php` is red from two independent causes in two files (an integer cast that truncates the coupon percentage; `withTrashed()` counting a removed line); either fix alone leaves it red with the other's message. The hand-back has the hypotheses table with two kept rows and at least one rejected row with evidence, `Root cause 1` and `Root cause 2` with file:line, a regression test line red before and green after, `Tests: <n> passed`, and no fourth round.

The fixtures' stand-in `vendor/bin/pest`, `vendor/bin/phpstan` and `vendor/bin/pint` are sh scripts (no PHP, no database); the stand-in pest of the debugger fixture adds an `expect-absent` marker (documented in its `CLAUDE.md`). Each fixture links `.claude/skills` to `resources/boost/skills`.

`evals/fixtures/release-samples/<case>/pass.md` is a hand-back that must satisfy the case; each `fail-*.md` is a planted bad one that must not, each for its own reason (the expected reason is pinned in `test_s9.py`, `PLANTED`).

## 5. Ambiguities resolved by the gate writer

1. **Separate case file.** `review-debug.json`, not `agents.json`: S8's schema test applies S8's key list and builder rules to every case in `agents.json`, and its agent-exists test would turn red on main.
2. **A `setup` key** (new): a review case needs a gate commit in history, which a single-commit copy cannot have, and a diff that is uncommitted. Documented above for the S11 runner.
3. **The debugger's AC.** The PRD gives the debugger R17 but no AC. Its case carries `R17`.
4. **The deep reviewer's exemption is by name, not by cap line alone** (section 2.1): a plain reviewer with a cap line still fails.
5. **Debugger and tinker.** R25's "never tinker" names read-only agents; the debugger is not one. It disallows `Agent` and `record-rule` only, and states that it prefers a test to tinker through the S8 builder's wording where it needs to. Not pinned.
6. **The plain reviewer also flags an avoid package** (R14 names planning and building; AC18 names the deep reviewer). Cheap, and a reviewer that misses a package the register marks avoid is wrong.
7. **Isolation is judged on the tip.** A reviewer that took the base's phpunit.xml would rerun against a database the builder's diff made reachable. The fixture plants exactly that.
8. **Reruns name their commands.** G5 reruns "each gate command the hand-back or plan names"; with none named, the report says `claimed, not rerun (no gate command named)`. An unfiltered full run is never started on the reviewer's own initiative.
9. **Single-pass wording for a deep review on a fixture with no DDEV:** the cases tell the agent the runner, as S8's did.
10. **Size caps.** Every agent at most 48 KB (the budget script); no separate cap for the reviewers (they are not checkers).

## 6. Not covered here

- G9 and G10 are pending in the reference itself.
- The outside-builder path (AC26, AC28) is slice S10.
- The release runner, the facts check and the benchmark are S11.

## 7. Round 2 (`tests/gate/test_s9_round2.py`)

Found when the reviewer ran on a real PR. Each statement is behaviour a real agent must follow; the tests check that the agent's text carries it. What a model does with the text is S11's job. Also fixed here: `tests/gate/test_s9.py` now puts its own folder on `sys.path`, so `python3 -m unittest tests.gate.test_s9` works from the repo root (an authorised gate amendment).

### 7.1 Several gate commits (reviewer, deep reviewer, builder, debugger), blocker

A slice can have several gate commits (`test(gate): AK-S1`, `test(gate): AK-S1 round 2`). The agent text says so, and:
- the gate files are the union of every `test(gate):` commit in `<base>..HEAD` whose message names the slice, or of the gate commits the brief (or caller) names;
- commits the brief names win: a forged or late `test(gate):` commit must not redefine the gate;
- each gate commit is lock-checked, in both forms (`git diff --quiet <gate commit> -- <gate files>` and `git diff --quiet <gate commit> HEAD -- <gate files>`);
- paths are literal: `:(literal)` pathspecs, or a per-path existence check in the gate commit (a path that exists nowhere compares clean, exit 0);
- exit 128 (a bad revision or pathspec) is an error to report, never a pass.

The builder's text drops the single-gate-commit assumption in the same way (its supplied-commit flow too).

### 7.2 Reviewers

- Untracked files: `git status --porcelain -uall` (a bare `--porcelain` hides files inside untracked directories); the deep reviewer's line counts include untracked files.
- PR or ref-range mode: when the brief names a PR or a ref range, diff `git diff <base> <head>` and ignore working-tree state (or ask); find the default branch with `gh pr view --json baseRefName`, or ask; never guess it.
- Reruns: only `vendor/bin/pest` or `ddev exec vendor/bin/pest`, with `--filter`; anything else is reported `claimed, not rerun (command not a filtered pest run)`. With no named command, the plan's slice gate or the CI step supplies it. A rerun while the lock check exit is 1 is labelled as running weakened tests.
- G8: a read-only reviewer reasons from the test and the changed lines, or raises a `Verify:` Suggestion that gives the exact revert command for a person to run.
- Bash forbid lists add `git restore`, `git clean`, `git apply`, `git rebase`, `git merge`, `git pull` and `git diff --output=`.

### 7.3 Deep reviewer

- Static checks: an error in an unchanged file that references a changed symbol is kept, or flagged `unverifiable: review by hand`; an old error is never dropped without a baseline.
- Every lens brief gets the Sensitive paths and Evidence rules pasted in.
- Deterministic findings (lock check, avoid package, check-backed) cannot be refuted by the challenger.
- With zero Critical or Important findings no challenger runs and the report line is `Challenge: none (no Critical or Important findings)`.
- Agent starts are limited by instruction (the checker type only, at most 5), and a retry counts against the cap.
- The mode lines carry the static-check summary and the left-out counts: `Mode: single pass (<reason>) · static checks: <summary, n left out>`; the team line likewise.

### 7.4 Debugger

- `git bisect` only with the caller's go, plus a restore to the original ref; otherwise only `git log -p`, `git blame` and `git show`.
- Gate files are identified as in 7.1.
- The regression test goes in a new file, never in a gate file.
- A hypothesis cycle with no surviving hypothesis counts as a round under the 3-round cap.
- `migrate` or any write to the dev database needs the caller's go.

### 7.5 Budget script

The exemption is the exact name `laravel-reviewer-deep`, not a suffix. Fixture `evals/fixtures/agent-other-reviewer-deep` (`acme-reviewer-deep`, inherits Agent, has a cap line) must fail with `must disallow Agent`; the orchestrator fixture still passes.

## 8. Round 3 (`tests/gate/test_s9_round3.py`)

Each git fact below is shown by a real temp-repo test (`GitFacts`); the agent-text tests check that the agents follow the safe method. Rulings 1, 2 and 5 apply to the reviewer, deep reviewer, builder and debugger; 3 and 4 to both reviewers; 6 and 7 to the deep reviewer (the plain reviewer never runs phpstan, so 7 is not pinned there).

1. **Subject-only matching.** Gate commits are found with `git log --format='%H %s'` and each subject is checked literally: the slice id is compared as a string, never as a raw regex (or it is escaped). A body line `test(gate): S1` does not make a commit a gate commit (`--grep` matches bodies), and the slice id `AK-S.` does not match `AK-S1`. The old `git log --grep '^test(gate): <slice>'` form is gone.
2. **Renames and deletions.** Gate files are listed with `--no-renames` or `--name-status`, so a renamed file's old path is not attributed to the earlier commit. Each file is checked against the last gate commit that touched it in which the file exists; a file a later gate commit deleted is not a gate file.
3. **`GIT_OPTIONAL_LOCKS=0`** applies to every git command the reviewers run (exported once or prefixed on each): `status`, `diff`, `ls-files`, `log`. A plain `git status` rewrites the index.
4. **PR mode base.** `origin/<baseRefName>` after a fetch, or the PR's merge base; never a possibly stale local branch.
5. **Excluded commits.** A gate commit the brief explicitly excludes is reported, never used.
6. **No challenger when every Critical or Important finding is deterministic** (lock check, avoid package, check-backed), with the line `Challenge: none (all findings deterministic)`. The round 2 line `Challenge: none (no Critical or Important findings)` stays for the zero case.
7. **phpstan cache writes** are the one stated exception to the no-file-writes rule in the deep reviewer's Bash text.
