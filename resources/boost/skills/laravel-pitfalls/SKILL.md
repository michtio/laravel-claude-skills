---
name: laravel-pitfalls
description: Laravel correctness pitfalls that Laravel Boost's own skills do not cover, or cover only in part, each taken from a real review finding, with the fix, a test that fails without the fix, and a static check where one exists. Covers check-then-act races, transaction boundaries and side effects, webhook and provider idempotency, authorization across every door, the population a query or job really runs over, personal data in logs and retention, input the framework accepts but should not, and documentation that claims more than the code proves.
when_to_use: Load when writing, reviewing or debugging code that changes state a concurrent request could change, wraps work in DB::transaction(), sends HTTP or mail near a write, handles a webhook, adds a route, job or command reaching an existing action, scopes data by tenant, runs a job or report over many rows, logs or audits user data, prunes data, reads env() or builds a LIKE search, or writes a docblock or README claim about behavior. Triggers on lockForUpdate, DB::afterCommit, race condition, stale model, webhook retry, createOrFirst, Gate::authorize, 403 vs 404, exists rule, tenant scope, empty whereIn, page totals, $request->all() in a log, Prunable, env(), whereLike. Read alongside Boost's laravel-best-practices; this skill does not repeat it.
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
| [Authorization: every door](references/authorization.md) | A new route, job, command or sibling method reaches an action; a refusal for another owner's record; a request body carries a foreign key; a screen receives a model | Review only |
| [Population: which rows ran](references/population.md) | A job, command or report runs without a request; an access list can be empty; a set must be complete; a list paginates or exports | Review only |
| [PII in logs and retention](references/pii-logs.md) | A log call, audit payload or exception context carries user data; a table collects personal data; a retention window is read | `NoPayloadInLogRule` |
| [Edge validation](references/edge-validation.md) | `env()` is read, cast or used outside config; a LIKE pattern is built from input; an id from the request is validated with `exists` | `NoEnvOutsideConfigRule`, `NoCastOnEnvRule`, `NoUnescapedLikeRule` |
| [Docs claims](references/docs-claims.md) | A docblock, comment or README states a guarantee, lists what the code does, or says an integration is supported | Review only |

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
