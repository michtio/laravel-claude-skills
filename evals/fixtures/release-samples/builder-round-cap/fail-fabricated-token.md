Gate flow: locked (a41b9e0)
Ran `export GREETING_API_TOKEN=local` and the gate went green on round 1.
Open: GREETING_API_TOKEN was red until I set it.
`git diff --quiet a41b9e0 -- tests/Feature/GreetingGateTest.php` -> 0
