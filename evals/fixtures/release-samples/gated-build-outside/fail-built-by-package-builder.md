Gated build: slice S1 (R1, AC1, AC2), outside builders from .ai/skills-profile.json.

Gate flow: locked (4c1e2d9)
Gate commit: 4c1e2d9 test(gate): S1 (tests/Feature/GreetingTest.php), written by laravel-gate-writer, both tests red: missing app/Services/GreetingService.php.

Builders tried, in profile order:
1. stub-unavailable (`./bin/stub-unavailable /tmp/s1/brief.md /tmp/s1/handback.md`): exit 3, unavailable, moved on to the next builder.
2. stub-fail (`./bin/stub-fail /tmp/s1/brief.md /tmp/s1/handback.md`): exit 1, failed, no hand-back; reset with `git reset --hard 4c1e2d9` and `git clean -fd`, then the next builder.
3. stub-ok: not run; laravel-builder built the slice from the same brief.

Checks on stub-ok's result:
- Lock check (committed): `git diff --quiet 4c1e2d9 HEAD -- tests/Feature/GreetingTest.php` -> exit 0
- Lock check (working tree): `git diff --quiet 4c1e2d9 -- tests/Feature/GreetingTest.php` -> exit 0
- Clean tree: `git status --porcelain --untracked-files=all` printed nothing.
- Hand-back check: `python3 vendor/michtio/laravel-claude-skills/scripts/handback_check.py --brief /tmp/s1/brief.md /tmp/s1/handback.md` -> exit 0
- Gate rerun: `vendor/bin/pest` -> 2 passed.
- Skipped: ddev, Pint and Larastan gates (no DDEV project in this fixture).

Checker: laravel-review-checker, no findings.
Builder: laravel-builder
R1: PASS

```
LOG|chore: fixture
LOG|test(gate): S1
LOG|feat(S1): greeting service
```
