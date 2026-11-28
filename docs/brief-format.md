# Brief and hand-back format

This page defines two plain-text documents: the brief a builder receives and the hand-back it writes. Any builder can use them, human or AI, local or hosted. The builder reads one brief file, builds one slice, and writes one hand-back file. How a builder is called, and what its exit code means, is in [outside-builders.md](outside-builders.md).

## The brief

A brief is a markdown file. The header fields come first, one per line, as `Name: value`.

| Field | Meaning |
|---|---|
| `Slice:` | The slice id, for example `S1`. |
| `Gate commit:` | The commit that holds the locked gate tests, or `none` when the builder writes its own tests. |
| `Gate files:` | The test files in that commit, on this one line, separated by single spaces. A path with a space cannot be listed, so a gate file never has one. |
| `Pest command:` | The command that runs the gate, for example `ddev exec vendor/bin/pest` or `vendor/bin/pest`. Run it exactly as written, from the project root. |
| `Project root:` | The absolute path of the project. Work only inside it. |
| `Laravel version:` | The Laravel version the code must target. |

After the fields, each requirement is a level-2 heading, followed by its text and its acceptance criteria, copied verbatim from the spec:

```
## R<n>

The requirement text (MUST or SHOULD).
AC<n>: Given ..., when ..., then ...
```

A heading may carry a title after a colon or a dash (`## R5: Reject unknown status`). A level-3 heading is never a requirement.

Then two more sections:

- `## Pointers`: file paths the builder reads before it writes code (the project's conventions and known pitfalls).
- `## Rules`: always these four.
  - Never edit a gate file.
  - Stop at a passing gate.
  - At most 3 rounds.
  - Commit your work before writing the hand-back.

When the suite is not isolated (the tests can reach the dev database), `## Rules` adds a fifth rule: "The suite is not isolated: never run a test that uses `RefreshDatabase`, `DatabaseMigrations`, `DatabaseTruncation` or `LazilyRefreshDatabase`, and never run `migrate:fresh` or `db:wipe`." A builder never changes the files that decide isolation (`phpunit.xml`, `phpunit.xml.dist`, `tests/Pest.php`, `tests/TestCase.php`, `.env`, `.env.testing`, `testbench.yaml`, `config/database.php` and the phpunit bootstrap file (unless it is under `vendor/`)); the caller compares them before every gate run, and a change disqualifies the builder.

A later round appends a `## Findings (round <n>)` section with what sent the slice back: uncommitted files, the hand-back checker's messages, the red gate output or review findings.

## Working rules

1. Read every pointer first.
2. Run the Pest command. It must fail before you build and pass when you stop.
3. Edit only files that are not gate files. A gate test that looks wrong is reported in the hand-back, never changed.
4. Stop as soon as the gate passes. Do not add scope.
5. Commit your work before writing the hand-back. The caller reviews the commits after the gate commit, and a dirty tree (any modified or untracked file) sends the slice back to you.

## The hand-back

After the work, write the hand-back file. It has exactly these five kinds of line. Each starts at the beginning of its line, in plain text, with no list marker, no bold and no code fence in the real file:

```
Gate flow: locked (<sha>)
Lock check (committed): exit <n>
Lock check (working tree): exit <n>
R<n>: PASS|FAIL|PENDING
Builder: <name>
```

- `Gate flow:` is `locked (<sha>)` when the brief has a gate commit (`<sha>` is 7 to 40 hex characters and must match the brief's `Gate commit:`; one may be a prefix of the other). It is `builder-written (<reason>)` when the brief says `Gate commit: none`, for example `Gate flow: builder-written (no gate tests for this slice)`.
- `Lock check (committed):` is the exit code of `git diff --quiet <gate commit> HEAD -- <gate files>`: your commits against the gate commit.
- `Lock check (working tree):` is the exit code of `git diff --quiet <gate commit> -- <gate files>`: your working tree and index against the gate commit. A gate file marked skip-worktree or assume-unchanged hides its edits from this command, so such a flag counts as exit 1.
- Run both lock checks from the repository root, with each gate file written as a literal pathspec, `:(literal)<path>`. Exit 0 means untouched; any exit other than 0 or 1 is a broken check, never a pass.
- Both lock lines are required when the flow is `locked`. Each must be `exit 0`. A nonzero code means a gate file changed, and the slice does not pass. With `builder-written` they are not required.
- One `R<n>:` line per `## R<n>` heading in the brief, with exactly one status. An `R<n>:` line for an id that is not in the brief is rejected.
- `Builder:` is your name, on one line.

Status meanings:

- `PASS`: the requirement is met and its acceptance criteria hold under the gate.
- `FAIL`: you tried and the requirement is not met.
- `PENDING`: you did not get to it, or you are blocked.

A slice passes only when every `R<n>` line is `PASS`. `FAIL` and `PENDING` are valid lines, so report them honestly.

Format rules:

- Each required line appears exactly once. A duplicate is rejected.
- A line must start at column 0, with nothing before it.
- Lines inside a fenced code block (three backticks or three tildes) are ignored, so the real file must not put them in one.
- Any other text is allowed (notes, a disputed gate test with its line and reason) when it does not start with one of the line shapes above.

A complete sample hand-back for a brief with R2 and R5 and a gate commit `3f2a9c1`:

```
Gate flow: locked (3f2a9c1)
Lock check (committed): exit 0
Lock check (working tree): exit 0
R2: PASS
R5: PASS
Builder: sample-builder
```

## Check

`python3 scripts/handback_check.py --brief <brief-file> <handback-file>` checks the form. In a project that installed the package with Composer, the script is at `vendor/michtio/laravel-claude-skills/scripts/handback_check.py`. It needs Python 3.9 or later and nothing else.

| Exit | Meaning |
|---|---|
| 0 | every required line is present and well formed |
| 1 | one message per problem: `missing line: ...`, `bad line: ...`, `bad status: ...`, `duplicate line: ...`, `unknown line: ...` or `gate touched: ...` |
| 2 | a usage error: no `--brief`, a file that cannot be read, or a brief with no `## R<n>` heading |

A hand-back that is missing a line does not count as a pass, whatever else it says. The check covers the form only: the caller still reruns the gate and both lock checks itself, because a hand-back is a claim, not evidence.
