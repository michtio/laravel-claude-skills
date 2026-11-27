Gate flow: locked (3f9a1c2)

Gate commit: 3f9a1c2 test(gate): S1
Files: tests/Feature/GreetingGateTest.php
| AC | test | red reason |
| AC1 | it greets Ada | missing app/Services/GreetingService.php |
| AC2 | it greets the world for an empty name | missing app/Services/GreetingService.php |

Built: app/Services/GreetingService.php
Pest: green, 2 passed (round 1).

Lock check (exit 0 means untouched):
- `git diff --quiet 3f9a1c2 HEAD -- tests/Feature/GreetingGateTest.php` -> 0
- `git diff --quiet 3f9a1c2 -- tests/Feature/GreetingGateTest.php` -> 0

Revert-to-prove: it greets Ada red with the fix reverted (missing app/Services/GreetingService.php), green with it.

Checker: skipped (small diff, nothing sensitive) · agents: 2

| R id | acceptance criterion | evidence | result |
| R1 | AC1, AC2 | vendor/bin/pest | PASS |
