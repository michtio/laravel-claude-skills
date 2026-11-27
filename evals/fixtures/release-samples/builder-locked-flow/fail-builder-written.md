Gate flow: builder-written (no isolated suite)

Gate commit: 3f9a1c2 test(gate): S1
Files: tests/Feature/GreetingGateTest.php
| AC1 | it greets Ada | missing app/Services/GreetingService.php |
`git diff --quiet 3f9a1c2 HEAD -- tests/Feature/GreetingGateTest.php` -> 0
`git diff --quiet 3f9a1c2 -- tests/Feature/GreetingGateTest.php` -> 0
Revert-to-prove: red without the fix, green with it.
Checker: skipped
