# Gate contract: outside builders

Requirements R18, R26, R27; acceptance criteria AC26, AC27, AC28 of `internal-docs/specs/2026-11-26-laravel-layer/prd.md`. Plan: the outside-builders slice (the gated-build skill, `docs/brief-format.md`, `docs/outside-builders.md`, the hand-back checker, the stub builders and the release case `gated-build-outside`). Package tooling lives in `scripts/`, never a root `bin/` (decisions log 2026-11-27, AD10 amended), so the plan's `bin/handback_check.py` is `scripts/handback_check.py` and its `bin/check.sh` is `scripts/check.sh`.

The gate is written before the builder starts. The builder implements to this contract and never edits the gate files below or the test configuration; under G3 it may add its own tests, each failing first. A change to a gate file goes back to the gate writer.

An outside builder is a program other than the package's own builder that builds one slice from a brief: a local AI, a script, a person, or a team tool such as the one in the team plugin (pack-integration AD3). The protocol is the Craft pack's, so one team tool serves both packs: call form `<command> <brief-file> <handback-file>`; exit 0 done, 3 unavailable, any other exit failed; no exit within `timeout_minutes` counts as failed.

**Where the protocol values come from** (accepted at the first gate review, so one team tool serves both packs): the call form, the exit codes, the hand-back lines (`Gate flow`, both `Lock check` lines, `R<n>: PASS|FAIL|PENDING`, `Builder:`), the checker's messages and exit codes 0, 1 and 2, the brief fields, and the reset before each builder all come from the Craft pack (`craftcms-claude-skills`: `docs/brief-format.md`, `docs/outside-builders.md`, its hand-back checker) and from the team integration spec, pack-integration AD3 (the outside-builder command and its exit codes) and AD4 (brief and hand-back translation, the packs' checker run before exit 0). The Laravel PRD states none of these values; only `Laravel version:` replaces the Craft pack's `Craft version:`.

Run, from the repo root:

```
python3 -m unittest discover -s tests/gate -p 'test_handback_check.py'          # AC27, R26
python3 -m unittest discover -s tests/gate -p 'test_brief_and_handback_docs.py' # R26, R18, R27
python3 -m unittest discover -s tests/gate -p 'test_gated_build_skill.py'       # AC26, AC27, AC28, R18, R27
python3 -m unittest discover -s tests/gate -p 'test_outside_builder_stubs.py'   # AC26, AC27, AC28
python3 -m unittest discover -s tests/gate -p 'test_gated_build_release_case.py' # AC26, AC28
sh scripts/check.sh
python3 -m unittest discover -s tests/gate
```

Gate files: `tests/gate/outside_builder_support.py` (shared paths and helpers), the five test files above, this contract, and and the fixtures, placed as the S8 and S9 release cases and the Craft pack place theirs: `evals/fixtures/gated-build/` (the fixture project, stubs in its `bin/`), `evals/fixtures/handback/` (hand-back fixtures), `evals/behavior-sets/outside-builders.json` (the release case, its own file because `agents.json` requires an agent per prompt) and `evals/fixtures/release-samples/gated-build-outside/` (its samples). The release runner reads every release case from `evals/behavior-sets/`.

## 1. Hand-back checker (`test_handback_check.py`)

`python3 scripts/handback_check.py --brief <brief> <handback>`, standard library only. Exit 0: well formed. Exit 1: a required line is missing, bad, duplicated or unknown, one message per problem. Exit 2: usage error (no arguments, no `--brief`, an unreadable file, a brief with no `## R<n>` headings). It checks form only: a `FAIL` or `PENDING` status is well formed; whether the slice passed is the gated build's decision.

Required lines, each at line start, outside code fences: `Gate flow: locked (<sha>)` or `Gate flow: builder-written (<reason>)`; `Lock check (committed): exit <n>` and `Lock check (working tree): exit <n>` when the flow is locked, each `exit 0` (nonzero is `gate touched`); one `R<n>: PASS|FAIL|PENDING` per `## R<n>` heading of the brief; `Builder: <name>`. The brief's `Gate commit:` binds the flow (a sha: locked with a matching sha, one a prefix of the other; `none`: builder-written). Duplicates, fenced lines, unknown R ids and a UTF-8 BOM behave as in the Craft pack's checker.

| Fixture (`evals/fixtures/handback/`) | Brief | Exit | Output contains |
|---|---|---|---|
| `missing-lock-line.md` (AC27) | `brief.md` | 1 | `missing line: Lock check (working tree)` |
| `missing-committed-lock-line.md` (AC27) | `brief.md` | 1 | `missing line: Lock check (committed)` |
| `missing-both-lock-lines.md` (AC27) | `brief.md` | 1 | both lines above |
| `missing-gate-flow.md` | `brief.md` | 1 | `missing line: Gate flow` |
| `missing-r-line.md` | `brief.md` | 1 | `missing line: R5` |
| `bad-status.md` | `brief.md` | 1 | `bad status: R2` |
| `missing-builder.md` | `brief.md` | 1 | `missing line: Builder` |
| `lock-nonzero.md` | `brief.md` | 1 | `gate touched` |
| `flow-downgrade.md`, `wrong-sha.md` | `brief.md` | 1 | `bad line: Gate flow` |
| `dup-r.md` | `brief.md` | 1 | `duplicate line: R2` |
| `dup-lock.md` | `brief.md` | 1 | `duplicate line: Lock check (working tree)` |
| `dup-flow.md` | `brief.md` | 1 | `duplicate line: Gate flow` |
| `fenced.md` | `brief.md` | 1 | `missing line: Gate flow` |
| `unknown-r.md` | `brief.md` | 1 | `unknown line: R9` |
| `complete.md`, `complete-bom.md` | `brief.md` | 0 | |
| `complete-builder-written.md` | `brief-none.md` | 0 | |
| `complete.md` | `brief-fenced-example.md` | 0 | |

`scripts/check.sh` gets one `gate` line running the checker on `complete.md` and one `must_fail` line, on one line each, running it on `missing-lock-line.md` with the pattern `missing line: Lock check (working tree)` (the plan's verification gate for AC27).

## 2. Docs (`test_brief_and_handback_docs.py`)

- `docs/brief-format.md`: the header fields `` `Slice:` ``, `` `Gate commit:` ``, `` `Gate files:` ``, `` `Pest command:` ``, `` `Project root:` ``, `` `Laravel version:` ``; requirements as `## R<n>` headings with their acceptance criteria verbatim; `## Pointers`; `## Rules` with the four rules and "Commit your work before writing the hand-back."; the five hand-back line shapes literally (`Gate flow: locked (<sha>)`, `Lock check (committed): exit <n>`, `Lock check (working tree): exit <n>`, `R<n>: PASS|FAIL|PENDING`, `Builder: <name>`), both lock-check commands, `handback_check.py --brief <brief-file> <handback-file>`, one line saying a hand-back that is missing a line does not count as a pass, and one saying a slice passes only when every `R<n>` is `PASS`.
- `docs/outside-builders.md`: the call form `<command> <brief-file> <handback-file>`; an exit-code table with rows `| 0 |` done, `| 3 |` unavailable and next builder, `| other |` (or `| any other |`) failed and next builder; `timeout_minutes` counts as failed; builders run in the profile's order and `laravel-builder` builds from the same brief when every outside builder fails; both lock-check commands, `handback_check.py` and 3 rounds.
- Standalone (R26, readable by a builder that is not Claude): neither file names assistant-only tooling (`Skill tool`, `Agent tool`, `subagent`, `CLAUDE_PLUGIN_ROOT`, `TodoWrite`) or a model or team tool (decisions log 2026-11-27: "local AI", never a named model).
- `docs/profile.md`: its `builders` example no longer shows the `{brief}` placeholder, which contradicts the call form, and it points to `outside-builders.md`.

## 3. Skill (`test_gated_build_skill.py`)

`resources/boost/skills/laravel-gated-build/SKILL.md`, frontmatter `name: laravel-gated-build` and a description, passing `scripts/validate-skills.sh`, naming no model or team tool. One line each (paragraph or bullet), by operative words:

- `laravel-gate-writer` runs first, before any builder, and the gate commit is `test(gate): <slice id>` (AC26);
- the builders are the profile's `builders` in `.ai/skills-profile.json`, in order;
- each builder is called as `<command> <brief-file> <handback-file>` with a brief in the format of `docs/brief-format.md` (AC26);
- both lock checks, `git diff --quiet <gate commit> HEAD -- <gate files>` and `git diff --quiet <gate commit> -- <gate files>` (AC26);
- `handback_check.py`: a hand-back with a missing line is reported and not a pass (AC27); the hand-back check runs before the checker (R26);
- `laravel-review-checker` runs on the outside builder's result (AC26, R18); 3 rounds per builder (R18);
- exit 3: next builder; any other exit: next builder; no exit within `timeout_minutes`: failed, next builder (AC28, R27);
- the tree is reset before each builder: `git reset --hard` back to the base (the gate commit), so a failed builder's commits go, and `git clean -fd` for its untracked files;
- `laravel-builder` builds from the same brief when every outside builder fails (R27);
- the report names each builder tried with its exit or outcome, the build never stops silently, and the report carries `Builder: <name>` (AC28).

Where the skill finds the checker in a user's project (the Composer path `vendor/michtio/laravel-claude-skills/scripts/handback_check.py`, the plugin root, or both) is the builder's choice; the release fixture links `vendor/michtio/laravel-claude-skills/scripts` to the package's `scripts/` so the Composer path resolves there.

## 4. Stubs (`test_outside_builder_stubs.py`)

The stubs live in `evals/fixtures/gated-build/bin/` and speak the call form. Each test copies the fixture into a throwaway git repository, adds a gate commit `test(gate): S1` with `tests/Feature/GreetingTest.php`, writes a brief outside the tree and runs the stub from outside the project.

- `stub-unavailable`: exit 3 (the unavailable row of `docs/outside-builders.md`), no hand-back, no commit, no file left behind (AC28).
- `stub-fail`: reads the brief's Project root, commits `wip(S1): half-done greeting service (stub-fail)`, leaves the untracked `STUB-FAIL-PARTIAL.txt`, writes no hand-back and exits 1 (the `| other |` failed row of `docs/outside-builders.md`). After the reset the gated build makes before the next builder (`git reset --hard` to the gate commit, `git clean -fd`), the head is the gate commit and the tree is clean, and `stub-ok` run from the same brief builds the slice with a hand-back the checker accepts (AC28, R27).
- `stub-ok`: reads the brief's Project root, commits `feat(S1): greeting service (stub-ok)`, leaves the gate file and the tree clean, and writes a hand-back that `scripts/handback_check.py` accepts, with `Gate flow: locked (<gate sha>)`, both lock lines at `exit 0`, `R1: PASS` and `Builder: stub-ok` (AC26).
- `stub-bad-handback`: builds like `stub-ok` and exits 0, but its hand-back has no `Lock check` line; the checker exits 1 naming both missing lock lines (AC27).

## 5. Release case (`test_gated_build_release_case.py`)

`evals/behavior-sets/outside-builders.json` holds `gated-build-outside` (AC26, AC28) in the release-case format of `tests/Agents/CONTRACT.md` section 4, run by the release runner. Fixture: `evals/fixtures/gated-build`, copied (`copy_cwd`), whose profile names `stub-unavailable`, `stub-fail` and `stub-ok`, in that order, and whose prompt approves exactly those three commands; `phpunit.xml` forces a test database (isolated, so the flow is locked); `vendor/bin/pest` is the builder fixtures' stand-in, byte for byte; `.claude/skills` links to `resources/boost/skills`. Expected agents: `laravel-gate-writer` and `laravel-review-checker`; `laravel-builder` is forbidden; at most 4 agents; runs once.

The report must show the gate commit before stub-ok's commit in the pasted log, a locked flow, stub-unavailable skipped (exit 3, next builder), stub-fail failed (exit 1) with the build moving on to the next builder, `Builder: stub-ok`, a lock check at exit 0, the hand-back check passing and a `Checker:` line; it must not show a skipped checker, `Builder: laravel-builder` or `Builder: stub-fail`, a hand-back check at exit 1 or 2, stub-fail's commit in the pasted log, or its file (or a modified greeting service) in the pasted status. The test proves the case's facts hold against the skill and the docs, the case and its fixture are set up as stated, `release-samples/gated-build-outside/pass.md` passes and each `fail-*.md` fails for its own reason. What a model does with the skill is the release runner's job.
