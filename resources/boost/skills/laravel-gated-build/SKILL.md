---
name: laravel-gated-build
description: Builds one approved slice with the outside builders listed in .ai/skills-profile.json (a local AI, a script, a team tool) and keeps the package's gates. laravel-gate-writer locks the gate before any builder, each builder gets a brief file and writes a hand-back, the hand-back is checked, both lock checks and laravel-review-checker cover the result, at most 3 rounds per builder, and laravel-builder takes over when every outside builder fails, is unavailable, times out or is not confirmed.
when_to_use: Use only when .ai/skills-profile.json names builders and a slice is to be built. Triggers on outside builder, local AI builder, builders list, brief file, hand-back, handback_check, unavailable builder, timeout_minutes, builder fallback. Not for a build with no builders in the profile (start laravel-builder), and not for the project setup that reads the profile (claude-skills:setup).
---

# Gated build with outside builders

The main session runs this for one slice: the package's gate flow (gate writer, lock checks, checker gate, 3-round cap) with the build handed to the profile's outside builders, in order, and `laravel-builder` last. Protocol: `docs/outside-builders.md`; brief and hand-back formats: `docs/brief-format.md`. Both, and the scripts, ship in the package: `vendor/michtio/laravel-claude-skills/` in a Composer install (`<pkg>` below), else the package checkout.

- `python3 <pkg>/scripts/run_builder.py` runs one builder with its timeout.
- `python3 <pkg>/scripts/handback_check.py --brief <brief> <handback>` checks a hand-back's lines.

The build never stops silently: every skip, failure, fallback and skipped gate goes in the report.

## 1. Preconditions

1. **Spec gate.** PRD and plan both `status: approved`, the slice exists, and you have its R ids with their acceptance criteria verbatim. Otherwise stop and report what is missing.
2. **Profile.** Read `.ai/skills-profile.json`: `gate_tests` and each builder's `name`, `command` and `timeout_minutes` (30 when missing). A builder without a name or a command is skipped and reported.
3. **Scripts.** Neither scripts folder found: start `laravel-builder` as below (section 8) and say why.
4. **Gate flow.** Locked unless the profile sets `"gate_tests": "builder-written"`, `tests/Pest.php` is missing, or the suite is not isolated (`phpunit.xml`, else `phpunit.xml.dist`, forces a `DB_DATABASE` that is not the dev database, or sqlite `:memory:`, or a Testbench package sets no database). Otherwise builder-written, with the reason.
5. **Commands.** The Pest command: `ddev exec vendor/bin/pest` when the project runs on DDEV (`.ddev/`, or the profile's `laravel.runner`), else the command the caller or `CLAUDE.md` names; never guess one. The absolute project root. Any gate you cannot run (Pint, Larastan) is named in the report with the reason.
6. **Clean tree.** `git status --porcelain --untracked-files=all` prints nothing and `git ls-files -v | grep '^[a-zS] '` prints nothing (no skip-worktree or assume-unchanged flags); otherwise stop and report, since the resets would discard that work. Record the branch.
7. **Confirm the builder commands.** They come from the repository: print `<name>: <command> (timeout <n> min)` per builder and run none of them without an explicit yes to that printed list. The request counts as that yes only when it names every command exactly as the profile has it. No yes, a partial yes or a non-interactive run: no outside builder runs, `laravel-builder` builds the slice (section 8), and the report says `Skipped: <name> (not confirmed)` for each.

No profile, or no builders in it: start `laravel-builder` with the usual slice brief (it starts its own gate writer) and say why in one line. Before the first builder, tell the user not to edit the repository during the run: the resets discard any change.

## 2. Gate tests first

Locked flow: start `laravel-gate-writer` first, before any builder runs (`laravel-claude-skills:laravel-gate-writer` when the package is a plugin: use the name your agent list shows). Its brief, nothing else: the slice id, the R ids with their acceptance criteria verbatim, the Laravel and PHP versions, the project root and the Pest command. No design, planned class names or hints. Pass no `model`.

Then confirm `git log -1 --format=%s` is `test(gate): <slice id>` and `git show --name-status --no-renames --format= HEAD` lists only files under `tests/`. Record `<gate commit>` and `<gate files>`, and keep its `| AC | test | red reason |` table.

Builder-written flow: no gate writer, and the brief says `Gate commit: none`.

## 3. The brief file

Make a work folder outside the project root with `mktemp -d` (`<work>`), so resets never touch it. Write `<work>/brief.md` in the format of `docs/brief-format.md`: the fields `Slice:`, `Project root:`, `Laravel version:`, `Gate commit:`, `Gate files:` and `Pest command:`; one `## R<n>` section per requirement with its text and acceptance criteria verbatim; `## Pointers` (the project's `CLAUDE.md` and the skill files the slice needs, as absolute paths); `## Rules` with its four rules. Every builder gets the same brief.

## 4. Builders, in profile order

The builders are the profile's `builders` in `.ai/skills-profile.json`, tried in order. Each is called as `<command> <brief-file> <handback-file>`.

**Before each builder: reset.** `<base>` is the gate commit (locked) or the HEAD recorded before step 3. Check the branch is still the one recorded. Clear any flag a builder set: for each path `git ls-files -v | grep '^[a-zS] '` lists, run `git update-index --no-skip-worktree -- <path>` and `git update-index --no-assume-unchanged -- <path>`. Then `git reset --hard <base>` back to the base (the gate commit), so a failed builder's commits go, and `git clean -fd` from the project root removes its untracked files; the step 1.6 checks must print nothing again. Delete `<work>/handback-<name>.md`. Never reset during one builder's fix rounds.

**Run it:** `python3 <pkg>/scripts/run_builder.py --cwd <project root> --timeout-minutes <timeout_minutes> --command '<command>' --log <work>/log-<name>.txt <work>/brief.md <work>/handback-<name>.md`. Give the Bash call a timeout above `timeout_minutes`; run longer builders in the background and wait for the notice.

- Exit 0: done, go to section 5.
- Exit 3: unavailable, record `<name> (exit 3, unavailable)` and reset for the next builder.
- No exit within `timeout_minutes` (exit 124, `builder exit: timeout`): failed, record `<name> (timeout)`, next builder.
- Exit 64: a usage error of `run_builder.py`; fix the call and rerun, never a builder result.
- Any other exit: failed, record `<name> (exit <n>, failed)`, reset, next builder.

## 5. Right after every exit 0

In every round, in this order:

1. **Lock checks** (locked flow), from the repository root, each gate file written as `:(literal)<path>`: `git diff --quiet <gate commit> HEAD -- <gate files>` (committed) and `git diff --quiet <gate commit> -- <gate files>` (working tree), and `git ls-files -v -- <gate files>` lists no line starting with a lowercase letter or `S`. Record each exit. Nonzero disqualifies the builder: record `<name> (lock check failed)`, reset, next builder.
2. **Committed work.** `git status --porcelain --untracked-files=all` must print nothing. Otherwise a round: "Commit your work before writing the hand-back."
3. **Hand-back check:** run `handback_check.py` on the hand-back before the `laravel-review-checker` starts; exit 1 or 2 (a missing, bad or duplicated line, or no file) is reported with its messages and never counts as a pass: a round.
4. **Gate, rerun by you** with the Pest command. A red gate, or an `R<n>:` line that is not `PASS`: a round with the failing output. The hand-back is a claim, not evidence.

## 6. Checker gate

Start `laravel-review-checker` on the outside builder's result, as for the package's own builder (`laravel-claude-skills:laravel-review-checker` when the package is a plugin). Size the commits with `git diff --numstat <base>..HEAD`. Sensitive: request input reaching a write or a query, policies, gates and middleware, raw SQL, unescaped Blade, `$guarded` or `$fillable` changes, webhooks, auth flows, migrations on existing tables, `config/` and env keys.

- 50 lines or more: security and conventions, in one checker.
- Under 50 lines, anything sensitive: the security lens.
- Under 50 lines, nothing sensitive: the conventions lens. Outside work always gets a checker.

Brief it with the lens, the Laravel and PHP versions, the changed files with `git diff <base>..HEAD`, the gate commit and files, and the static and test results (or "not run" with the reason). Pass no `model`. At most 4 agents per run: the gate writer, the checker and up to two re-checks. Critical: a round, then one re-check. Important: send it in the round, or list it with the reason. Suggestions: list only.

## 7. Fix rounds

A round sends the problems back to the same builder: append `## Findings (round <n>)` to `<work>/brief.md`, delete the old hand-back and run the same command again with no reset; then section 5, and section 6 for a re-check. At most 3 rounds per builder; the count restarts for the next builder. Stop after 3 rounds: when the tree, the hand-back or the gate still fails, record `<name> (3 rounds, gate red)`, reset and go to the next builder. When only checker findings stay open, stop and report them: the slice is not passed.

## 8. Fallback: laravel-builder

When every outside builder failed, timed out, was unavailable, was disqualified or was not confirmed, reset and start `laravel-builder` (`laravel-claude-skills:laravel-builder` when the package is a plugin), which builds the slice from the same brief: give it the spec paths, the slice, its R ids and acceptance criteria and `<work>/brief.md`, and in the locked flow the gate commit and gate files, so it starts no second gate writer. Pass no `model`. It runs its own checker gate and round caps. Write its hand-back lines to `<work>/handback-laravel-builder.md`, run `handback_check.py` on it, and rerun section 5's lock checks and gate yourself.

## 9. Report

The report names each builder tried with its exit code or outcome, one item per line:

```
Gate flow: locked (<gate commit>)
Builder: <name>
Skipped: <name> (not confirmed); <name> (exit 3, unavailable); <name> (exit 1, failed); <name> (timeout); <name> (lock check failed); <name> (3 rounds, gate red) | none
Fallback: every outside builder failed, was unavailable or was not confirmed; laravel-builder continued from the same brief | none
Hand-back check: exit <n> (<pass, or the messages>)
Gate: <Pest command> <green or red> (<counts>)
Lock check (committed): exit <n>
Lock check (working tree): exit <n>
R<n>: PASS|FAIL|PENDING  <acceptance criterion> | <evidence>
Checker: <lens> · agents: <n> · fixed: <...> · open Important: <...>
Rounds: <n> of 3
Skipped gates: <gate> (<reason>) | none
```

`Builder: <name>` is the builder whose work passed, or `laravel-builder`. Add the gate writer's table, any disputed gate test with its line and reason, and open findings. Builder-written flow: `Gate flow: builder-written (<reason>)`, no lock lines.

A slice passes only when every `R<n>` is `PASS`, the hand-back check passed, the gate is green under your own run and both lock checks are `exit 0`. Passing means ready for review, never done: that is the owner's call.
