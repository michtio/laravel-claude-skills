# Gate contract, slice S1 (laravel-layer)

Requirements: R3, R15, R19. Acceptance criteria: AC4, AC19, AC7. Architecture: AD1 to AD3, AD10 in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`.

The gate is written before the builder starts. The builder implements to this contract and never edits `tests/gate/` or `evals/fixtures/`. A change to the gate goes back to the gate writer.

Run from the repo root:

```
python3 -m unittest discover -s tests/gate   # unit gates, no DDEV, no network
sh scripts/check.sh                              # the package quality gate
bash tests/gate/fixture-app.sh               # fixture-app gate, needs DDEV
```

## 1. Tool interfaces (ported from `craftcms-claude-skills`)

Every check takes `--root DIR`, default the repo root. Under a root, skills live in `DIR/resources/boost/skills/<name>/SKILL.md` and agents in `DIR/agents/*.md`. A missing `agents/` or `resources/boost/skills/` directory means nothing to check there (exit 0 for that part).

### `python3 scripts/agent_budget.py [--root DIR]` (standard library, Python 3.9+)

Prints one line per agent (`ok  ` or `FAIL`) and a summary line. Exit 0 when no agent fails, exit 1 otherwise. Rules, with the exact substring each failure message contains:

| Rule | Message substring |
|---|---|
| Agent file plus its `skills:` preloads over 48 KB (checker 16 KB) | `over 48 KB` |
| `Agent` in `tools:` and no line matching `At most N agents per run` or `... per review` | `Agent tool without an 'At most N agents per run\|review' line` |
| Cap N above 5 | `cap above 5` |
| File name ending `-checker` or `-gate-writer` with `Agent` in `tools:` | `must not have the Agent tool` |
| Read-only agent (file name contains `planner`, `reviewer`, `checker` or `gate-writer`) whose `disallowedTools:` does not name `mcp__laravel-boost__tinker` | `must disallow mcp__laravel-boost__tinker` |
| Planner, reviewer, checker or gate writer without `Agent` in `disallowedTools:` and without a `tools:` allowlist that omits `Agent` (it would inherit Agent). Checker and gate writer | `must not have the Agent tool` |
| Same, planner and reviewer | `must disallow Agent` |
| Agent file without a closing `---` frontmatter fence | `no frontmatter` |
| Reviewer or checker with `effort` xhigh, quotes stripped (`"xhigh"` counts); message as in the ported tool | `reviewer agents use effort high, not xhigh` |
| Same agents whose `disallowedTools:` does not name `mcp__laravel-boost__record-rule` (it writes `.ai/rules`) | `must disallow mcp__laravel-boost__record-rule` |
| Planner, reviewer or checker whose `disallowedTools:` lacks `Write`, `Edit` or `NotebookEdit` | `must disallow Write, Edit, NotebookEdit` |

The gate writer writes tests, so it is exempt from the Write/Edit/NotebookEdit rule only, and must disallow tinker and record-rule like the others. **How Agent is detected.** The Agent tool counts in every form: `Agent`, `Agent(...)` with a restriction (commas inside the parentheses included), and the old name `Task` or `Task(...)`. Inline lists (`tools: Read, Agent(a, b)`) and block lists both count, and block items may start at column 0 (`- Agent`).

**Inheritance.** An agent with no `tools:` line inherits every tool, Agent included (plan AD3). So a planner, reviewer, checker or gate writer needs `Agent` in `disallowedTools` (or a `tools:` allowlist without it), and any other agent without a `tools:` line needs the cap line unless it disallows Agent.

**Role markers** (`-checker`, `-gate-writer`, and planner, reviewer, checker, gate-writer for the read-only rules) apply to both the file stem and the frontmatter `name:`. `effort` values are compared with quotes stripped.

An agent with no Agent tool, stated or inherited, has cap 0. Reviewer and checker agents never use `effort: xhigh` (as in the Craft tool). Tool access is by `disallowedTools` (AD3); agents in this package declare no `tools:` list naming a Boost tool.

### `bash scripts/validate-skills.sh [--root DIR]` (ruby, as in the Craft tool)

Validates every `DIR/resources/boost/skills/*/SKILL.md`: strict YAML frontmatter, known keys only, `name` equals the directory and is 1 to 64 chars of lowercase letters, digits and hyphens, `description` 1 to 1024 chars, listing (`description` + `" - "` + `when_to_use`) at most 1300 chars, body at most 12 KB. The Craft-only version-script checks are dropped. Exit 0 or 1. Message substrings:

| Rule | Message substring |
|---|---|
| Body over 12 KB | `SKILL.md body is` and `max 12288` |
| Listing over 1300 | `description + when_to_use is` and `max 1300` |

### `sh scripts/check.sh`

Runs every gate and exits 0 only when all pass. It defines `gate`, `must_fail` and `grep_ok` helpers as in the Craft pack. For S1 it runs `validate-skills.sh` and `agent_budget.py` on the repo, then one `must_fail` self-test per bad fixture, and a `gate` on the valid fixture. Each self-test line begins with `must_fail`, and names its fixture path (`evals/fixtures/<name>`) on the same line, so a checker that stops checking turns CI red. Later slices append their gates.

## 2. Fixtures (`evals/fixtures/`)

Each is a minimal tree. Each must-fail fixture violates exactly one rule.

| Fixture | Command (from repo root) | Exit |
|---|---|---|
| `agent-no-cap` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-no-cap` | 1 |
| `agent-checker-with-agent` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-checker-with-agent` | 1 |
| `agent-gate-writer-with-agent` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-gate-writer-with-agent` | 1 |
| `agent-cap-6` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-cap-6` | 1 |
| `agent-readonly-tinker` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-tinker` | 1 |
| `agent-readonly-record-rule` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-record-rule` | 1 |
| `agent-restricted-agent-no-cap` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-restricted-agent-no-cap` | 1 |
| `agent-task-alias-no-cap` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-task-alias-no-cap` | 1 |
| `agent-column0-list-no-cap` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-column0-list-no-cap` | 1 |
| `agent-no-tools-no-cap` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-no-tools-no-cap` | 1 |
| `checker-inherits-agent` | `python3 scripts/agent_budget.py --root evals/fixtures/checker-inherits-agent` | 1 |
| `planner-inherits-agent` | `python3 scripts/agent_budget.py --root evals/fixtures/planner-inherits-agent` | 1 |
| `agent-no-frontmatter` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-no-frontmatter` | 1 |
| `agent-name-field-checker` | `python3 scripts/agent_budget.py --root evals/fixtures/agent-name-field-checker` | 1 |
| `reviewer-effort-xhigh-quoted` | `python3 scripts/agent_budget.py --root evals/fixtures/reviewer-effort-xhigh-quoted` | 1 |
| `skill-body-over-12kb` | `bash scripts/validate-skills.sh --root evals/fixtures/skill-body-over-12kb` | 1 |
| `skill-listing-over-1300` | `bash scripts/validate-skills.sh --root evals/fixtures/skill-listing-over-1300` | 1 |
| `valid` | both commands above with `--root evals/fixtures/valid` | 0 |

Contents: `agent-checker-with-agent` holds `agents/laravel-review-checker.md`; `agent-gate-writer-with-agent` holds `agents/laravel-gate-writer.md`; `agent-readonly-tinker` holds a planner that disallows Write, Edit and NotebookEdit but not tinker; `agent-readonly-record-rule` holds a planner that disallows those and tinker but not record-rule. `valid` holds an orchestrator (cap 3), a planner, a checker, a gate writer and the skill `laravel-pitfalls`, all compliant.

The unit tests check the message substring as well as the exit code, so a fixture cannot pass by crashing.

## 3. Package skeleton assertions (unit tests)

- `.claude-plugin/plugin.json`: valid JSON, no `skills` key, `agents` is a non-empty list of paths ending `.md` (AD2, AD1). `claude plugin validate .` passing is a manual gate for the builder.
- `.claude-plugin/marketplace.json`: valid JSON.
- `composer.json`: name `michtio/laravel-claude-skills`; `laravel/boost` constraint `^2.5` in `require` or `require-dev`.
- `resources/boost/skills/laravel-pitfalls/SKILL.md`: frontmatter with `name: laravel-pitfalls` and a non-empty `description`.
- `.github/workflows/ci.yml`: runs `scripts/check.sh` and `python3 -m unittest discover -s tests/gate`; every `actions/checkout` and `actions/setup-python` is on major v5 or later. Any `@v4` or lower fails; a use without a `@vN` tag fails. The exact major is not pinned: the builder verifies the current ones and cites the releases.

## 4. Fixture-app gate (`tests/gate/fixture-app.sh`, needs DDEV, not a unittest)

Assumes `fixtures/app`: a Laravel app with Boost, its own `.ddev` (PHP 8.4), requiring this package through a Composer path repository. The script runs only `ddev` commands (`ddev start`, `ddev exec`, run from inside the app), never php, composer or npm on the host.

1. Checks `fixtures/app/.ddev/config.yaml` exists and DDEV is installed; otherwise exits 1 with a clear message.
2. Changes into `fixtures/app` (`ddev start` has no `--dir` flag and `ddev exec --dir` only sets the in-container directory), then starts DDEV.
3. Deletes `fixtures/app/.claude/skills/laravel-pitfalls` so the run proves the write.
4. Runs `ddev exec bash -c "php artisan boost:install --guidelines --skills --mcp --no-interaction"` (override with `BOOST_CMD`; the builder documents which command works, `boost:update --no-discover` being the alternative).
5. Asserts `fixtures/app/.claude/skills/laravel-pitfalls/SKILL.md` exists and is non-empty.
6. Prints `PASS` and exits 0, or prints `FAIL: <reason>` and exits 1.

AC4 in S1 covers the stub skill `laravel-pitfalls` only. House style and package verdicts arrive in later slices.

## 5. Spike-notes gate (local only)

`internal-docs/spikes/s1.md` is git-ignored. It must exist and carry three headings, each followed by a line starting `Result:` before the next heading:

1. `Preload of a project skill from a plugin agent`
2. `Boost MCP tool names`
3. `Pest custom presets`

The unit test is skipped when `internal-docs/` is absent (public clones, CI).

## 6. Layout

Tooling lives in `scripts/`, never `bin/`: a root `bin/` goes on the Bash PATH while the plugin is enabled and claude.ai and Cowork refuse such a plugin (https://code.claude.com/docs/en/plugins/manifest-reference, Standard layout). A unit test asserts the repo root has no `bin/` directory.
