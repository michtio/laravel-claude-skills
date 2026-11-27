# Docs claims: documentation that promises more than the code does

Gap: covered partly by Boost (laravel-best-practices, rules/style.md: "Write comments that explain why")

Boost says to keep comments accurate when behavior changes. It does not cover the failure that slips past that advice: a docblock, README or comment that states a guarantee ("idempotent", "tenant-safe", "never logs personal data", "supports provider X") that no test proves. Readers and agents trust the sentence over the code, and nothing turns red when the two drift apart.

## Pitfall 1: a behavior claim with no test behind it

```php
/**
 * Idempotent: safe to call twice for the same payment.
 */
public function record(array $event): void
```

The sentence was true when it was written, or was meant to be. Then a refactor moved the guard, and the docblock still says idempotent. A reviewer reads the claim and skips the check, and an agent repeats it in its hand-back.

### Fix

Every claim about behavior names the test that proves it. Delete any claim you cannot point to a test for.

```php
/**
 * Applies a provider payment event. A redelivered event is a no-op.
 * Proven by tests/Feature/Payments/PaymentWebhookTest.php ("applies a redelivered event once").
 */
public function record(array $event): void
```

The test then has to fail when the behavior is removed. A claim backed by a test that stays green with the fix reverted still proves nothing.

## Pitfall 2: a list in prose next to a condition in code

A docblock lists which attributes trigger a recalculation, while the method checks a hand-written condition. The first change updates one of them. After that, the documentation describes behavior the code does not have, and a static analyser cannot see the difference.

### Fix

Make the list code that the logic reads, and test the list:

```php
/** Attributes whose change re-posts the document. */
public const REPOST_ATTRIBUTES = ['amount_cents', 'tax_cents', 'issued_on'];

public function needsRepost(): bool
{
    return $this->isDirty(self::REPOST_ATTRIBUTES);
}
```

## Pitfall 3: "supports X" for an integration nobody has run

An adapter written from memory of a third-party API, and never run against the real service, gets listed as supported. When the request shapes are wrong it can produce nothing at all, with no error, and that looks like "no data" rather than "broken".

### Fix

Refuse rather than try. Keep the adapter behind a flag that a person sets after a real end-to-end run (`'verified' => env('CALENDAR_PROVIDER_VERIFIED', false)`), throw a clear exception while it is unset, and document it as unverified until then. Contract-test the adapter against responses recorded from the real service, not against shapes you wrote yourself.

## Pitfall 4: a deliberate oddity with no marker

Some behavior is deliberately inconsistent: kept for compatibility, or matching an external system. Without a note, the next reader "fixes" it and silently changes historical results.

### Fix

Put a comment on the method that carries the oddity. It should say that the behavior is deliberate, give the reason, and name the test that pins it, addressed to whoever tries to change it.

## How to test it

The test named in each claim is the test. To audit an existing codebase, search docblocks, comments and READMEs for guarantee words (`idempotent`, `always`, `never`, `safe`, `atomic`, `supports`) and look for the named test. Then revert the behavior on a scratch branch and confirm the test goes red.

## Check

Review only. Whether a sentence is a behavioral claim, and whether a test really proves it, needs judgement. For every docblock or README sentence that promises behavior, the review asks one question: which test fails if this stops being true?
