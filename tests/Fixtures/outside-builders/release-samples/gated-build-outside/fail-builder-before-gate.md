Gated build: slice S1 (R1, AC1, AC2), outside builders from .ai/skills-profile.json.

Gate flow: locked (4c1e2d9)
Gate commit: 4c1e2d9 test(gate): S1 (tests/Feature/GreetingTest.php), written by laravel-gate-writer, both tests red: missing app/Services/GreetingService.php.

Builders tried, in profile order:
1. stub-unavailable (`./bin/stub-unavailable /tmp/s1/brief.md /tmp/s1/handback.md`): exit 3, unavailable, moved on to the next builder.
2. stub-ok (`./bin/stub-ok /tmp/s1/brief.md /tmp/s1/handback.md`): exit 0 in round 1.

Checks on stub-ok's result:
- Lock check (committed): `git diff --quiet 4c1e2d9 HEAD -- tests/Feature/GreetingTest.php` -> exit 0
- Lock check (working tree): `git diff --quiet 4c1e2d9 -- tests/Feature/GreetingTest.php` -> exit 0
- Clean tree: `git status --porcelain --untracked-files=all` printed nothing.
- Hand-back check: `python3 vendor/michtio/laravel-claude-skills/scripts/handback_check.py --brief /tmp/s1/brief.md /tmp/s1/handback.md` -> exit 0
- Gate rerun: `vendor/bin/pest` -> 2 passed.
- Skipped: ddev, Pint and Larastan gates (no DDEV project in this fixture).

Checker: laravel-review-checker, no findings.
Builder: stub-ok
R1: PASS

```
LOG|chore: fixture
LOG|feat(S1): greeting service (stub-ok)
LOG|test(gate): S1
```
