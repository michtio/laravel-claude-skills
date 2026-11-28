# Outside builders

An outside builder is a program other than the package's own builder that builds one slice from a brief: a local AI running on your machine, a script, a person, or a team tool. The protocol below is the same for all of them and needs no particular tool. The brief it reads and the hand-back it writes are defined in [brief-format.md](brief-format.md).

## Naming builders

Outside builders are listed in the project profile, `.ai/skills-profile.json`, under `builders` (see [profile.md](profile.md)):

```json
{
    "version": 1,
    "builders": [
        {"name": "local", "command": "run-local-builder", "timeout_minutes": 30},
        {"name": "team", "command": "./bin/team-builder --quiet", "timeout_minutes": 60}
    ]
}
```

Each builder has a `name`, a `command` and an optional `timeout_minutes` (a number above 0; 30 when it is left out). Builders run in the order the profile lists them.

Because the profile is a file in the repository, nothing in it reaches a shell unchecked. `python3 scripts/builders_check.py --profile .ai/skills-profile.json --root <project root> --out <file>` skips, by position, any builder whose `name` does not match `^[A-Za-z0-9._-]{1,64}$`, whose `command` is empty or holds a control character (a newline, an escape sequence), whose `timeout_minutes` is not a number above 0, or whose name an earlier builder already has. It prints the usable ones as `<name>: <command> (timeout <n> min)` and writes them to `<file>`.

## Call form

```
<command> <brief-file> <handback-file>
```

The command receives two absolute paths, appended after whatever the profile's command already holds. It reads the brief, does the work in the project root named there, and writes the hand-back to the second path. It runs from the project root.

Because the command comes from a file in the repository, the caller prints every builder as `<name>: <command> (timeout <n> min)` and runs none of them without your explicit yes to that printed list. A request counts as that yes only when it names every command exactly as the profile has it. Without a yes, with a partial yes, or in a run nobody can answer, no outside builder runs: the package's own builder, `laravel-builder`, builds the slice, and the report says `Skipped: <name> (not confirmed)` for each. The caller runs only the builders it printed and you confirmed, and never reads the profile again during the run.

## Exit codes

| Exit | Meaning |
|---|---|
| 0 | done, hand-back written |
| 3 | unavailable (not installed, not running, no capacity): try the next builder at once |
| other | failed: try the next builder |

## Timeout

A builder that has not exited within `timeout_minutes` counts as failed: the caller kills it and everything it started, then tries the next builder. The package's `scripts/run_builder.py` runs one builder this way, taking the command, the timeout and the project root from the file `builders_check.py` wrote:

```
python3 scripts/run_builder.py --builders <file> --name <name> <brief-file> <handback-file>
```

A team tool that already holds the values can pass `--cwd <project root> --timeout-minutes <n> --command <command>` instead, as separate arguments. It exits with the builder's own code, 124 on a timeout, or 64 for a usage error of its own (never a builder result), and its last line is `builder exit: <n>` or `builder exit: timeout`.

## Before each builder

Each builder starts from a clean slice, so a failed builder leaves nothing behind for the next one. A suite that is not isolated and uses a database-wiping trait (`RefreshDatabase`, `DatabaseMigrations`, `DatabaseTruncation`, `LazilyRefreshDatabase`) runs no builder at all: the caller asks for a forced test database first.

1. The base is the gate commit, or, when the slice has none, the commit the slice started from.
2. Clear any skip-worktree or assume-unchanged flag (`git reset --hard` keeps them), then reset the tree to the base: `git reset --hard <base>` removes the failed builder's commits and edits, and `git clean -fd` removes its untracked files.
3. Delete any old hand-back file.

Within one builder's fix rounds the tree is kept, so the builder fixes on top of its own work.

## After the builder exits

After every exit 0, in every round, the caller checks in this order:

1. Both lock checks, from the repository root, each gate file as `:(literal)<path>`: `git diff --quiet <gate commit> HEAD -- <gate files>` and `git diff --quiet <gate commit> -- <gate files>`, and `git ls-files -v -- <gate files>` lists no line starting with a lowercase letter or `S` (a skip-worktree or assume-unchanged flag hides an edit from both). A nonzero code or a flag disqualifies the builder: reset, next builder.
2. A clean tree: `git status --porcelain --untracked-files=all` prints nothing. Uncommitted work sends the slice back to the same builder.
3. The hand-back checker: `python3 scripts/handback_check.py --brief <brief-file> <handback-file>`. A hand-back with a missing or bad line is not a pass, whatever else it says.
4. The test configuration: `python3 scripts/suite_guard.py verify --root <project root> --snapshot <file>`, against the snapshot taken before the first builder. A created, changed or deleted `phpunit.xml`, `phpunit.xml.dist`, `tests/Pest.php`, `tests/TestCase.php`, `.env` or `.env.testing` disqualifies the builder, and the gate is not run on its code.
5. The gate, rerun by the caller with the brief's Pest command. The hand-back is a claim, not evidence.
6. A review of the builder's commits, as for the package's own builder.

| Result | Action |
|---|---|
| exit 0, every check passes | the slice passes when every `R<n>` is `PASS`, both lock checks are `exit 0`, the gate is green and the review leaves nothing critical open |
| exit 0, a lock check nonzero or a changed test configuration | the builder is disqualified: reset, next builder |
| exit 0, dirty tree, hand-back rejected or gate red | another round for the same builder with the problems appended to the brief; at most 3 rounds, then reset and the next builder |
| exit 3 | next builder |
| other exit | next builder |
| timeout | kill the builder and what it started, then next builder |

## Order and fallback

Builders run in the order listed in the project profile. When all of them are unavailable, failed, timed out, were disqualified or were not confirmed, the package's own builder, `laravel-builder`, builds the slice from the same brief, against the same gate commit. A gated build never stops silently: the report names each builder tried with its exit code or outcome, and the builder whose work passed on a `Builder: <name>` line.
