---
name: laravel-pitfalls
description: Laravel correctness pitfalls that Laravel Boost's own skills do not cover, or cover only in part, each taken from a real review finding, with the fix, a test that fails without the fix, and a static check where one exists. Covers check-then-act races (lock and recheck), transaction boundaries and side effects that cannot be rolled back, and webhook and provider idempotency.
when_to_use: Load when writing, reviewing or debugging code that changes state a concurrent request could also change, wraps work in DB::transaction(), sends HTTP or mail near a database write, dispatches jobs or events from a write path, handles a webhook, or records money or other state a provider has already changed. Triggers on lockForUpdate, sharedLock, DB::transaction, DB::afterCommit, afterCommit(), ShouldDispatchAfterCommit, double submit, double click, race condition, stale model, read-modify-write counter, webhook retry, duplicate delivery, idempotency key, event_id, insertOrIgnore, createOrFirst, unique index as a guard. Read alongside Boost's laravel-best-practices; this skill does not repeat it.
---

# Laravel pitfalls

Each reference describes one class of pitfall: what goes wrong, why it is easy to miss, the fix with a Laravel 13 example, a test that goes red when the fix is reverted, and the static check that catches it where one exists.

Every reference opens with a gap line. `Gap: not covered by Boost` means Boost's skills say nothing about it. `Gap: covered partly by Boost (<rule>)` names the Boost rule it builds on. Read that rule first: this skill only adds what the rule leaves out. Anything Boost already covers fully is left out of this skill.

## Index

| Pitfall | Read when | Check |
| --- | --- | --- |
| [Concurrency: check then act](references/concurrency.md) | A guard (status, balance, "is editable") decides whether a write may happen, a counter is updated, or something may happen only once per period | Review item; no static check |
| [Transactions: boundaries and side effects](references/transactions.md) | Code inside `DB::transaction()` calls HTTP, sends mail, dispatches work, or a write that must be all-or-nothing spans more than one transaction | `NoSideEffectInTransactionRule` in `extension.neon` |
| [Idempotency: webhooks and providers](references/idempotency.md) | A webhook handler applies an event, or the app records something a provider has already done | Review item; no static check |

## Using the checks

Add the package's PHPStan extension to the application's `phpstan.neon` (Larastan or plain PHPStan 2):

```neon
includes:
    - vendor/michtio/laravel-claude-skills/extension.neon
```

Each rule's message ends with `See laravel-pitfalls: <reference>`, so a reported line leads straight to the reference above.

## When fixing one of these

1. Write the test from the reference first and watch it fail against the current code.
2. Apply the fix and watch the test pass.
3. Revert only the fix, watch the test fail again, then restore it. A test that stays green with the fix reverted proves nothing.
