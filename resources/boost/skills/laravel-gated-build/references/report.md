# Gated build report

The report of a gated build with outside builders, one item per line, plain text:

```
Gate flow: locked (<gate commit>)
Builder: <name>
Skipped: <name> (not confirmed); <name> (exit 3, unavailable); <name> (exit 1, failed); <name> (timeout); <name> (lock check failed); <name> (test config changed: <path>); <name> (wiping trait on a not-isolated suite); <name> (3 rounds, gate red) | none
Stopped: <path> changed by <name> survives the reset | none
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

- `Builder:` is the builder whose work passed, or `laravel-builder`.
- `Stopped:` is written when a file that decides isolation, changed by a builder, is still changed after the reset (a git-ignored file such as `phpunit.xml` or `.env`, which `git reset --hard` and `git clean -fd` leave alone). The build stops there. Tell the user to restore the file by hand (a tracked one with `git checkout <base> -- <path>`, an ignored one from their own copy) and to start the build again.
- Builder-written flow: `Gate flow: builder-written (<reason>)`, and no lock lines.
