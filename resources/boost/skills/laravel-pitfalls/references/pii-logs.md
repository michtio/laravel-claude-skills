# PII in logs, audit trails and retention

Gap: covered partly by Boost (laravel-best-practices, rules/architecture.md: "Use `Context` for request-scoped data"; rules/security.blade.php: "Encrypt sensitive attributes when appropriate")

Boost covers keeping data out of log context with `Context::addHidden()`, and keeping attributes out of serialization with `$hidden` and the `encrypted` cast. It does not cover the common leak, where a model or the request payload is passed straight to a log call, or what personal data may go into an audit trail. Nor does it cover how long any of this may be kept.

## Pitfall 1: the payload in the log

```php
Log::info('Order placed', ['order' => $order]);       // every visible attribute
Log::warning('Login failed', $request->all());          // the password, too
Log::error('Webhook rejected', ['request' => $request]);
```

A model in the context is serialized through `toArray()`: everything not in `$hidden`, which usually includes names, addresses and phone numbers. `$request->all()` holds whatever the client sent, including passwords on a login form, tokens and free text. Once written, that data is copied to every log store and aggregator and kept for as long as they keep logs. The database's retention and erasure rules do not reach it, and an erasure request cannot find it.

### Fix

Log ids and the few scalar fields that explain the event. For data that a later step needs but the log must not show, use hidden context:

```php
use Illuminate\Support\Facades\Context;
use Illuminate\Support\Facades\Log;

Log::info('Order placed', ['order_id' => $order->id, 'total_cents' => $order->total_cents]);
Log::warning('Login failed', ['email_hash' => hash_hmac('sha256', $email, $pepper)]);

Context::addHidden('customer_id', $order->customer_id); // reaches queued jobs, not the log
```

Exceptions carry context too: an exception's `context()` array is merged into the log entry when it is reported, so the same rule applies to what you put there.

## Pitfall 2: personal data in an audit trail

An audit or event log is kept longer than anything else, sometimes years, and is often append-only or hash-chained, so it cannot be cleaned up later. A name, email address, IP or user agent written there stays for the full retention period.

### Fix

Allowlist audit payloads to scalars that identify without describing: ids, codes, amounts, dates, kinds. When an audit must show that two events came from the same address or device, store a keyed hash (HMAC under a rotatable secret), never the raw value. When a data-subject request needs an answer, anonymise the person's rows rather than deleting records you are obliged to keep.

## Pitfall 3: data with no expiry, and an off switch that deletes everything

A table that collects personal data without an expiry is a defect, not housekeeping for later. The fix usually contains a second bug: the retention window is read and "made safe" with `max(1, $days)`, so a configured `0` meaning "keep forever" becomes a one-day window that deletes nearly the whole table on the next run.

### Fix

Give each table a window in config, next to the reason for the number, and prune with Laravel's `Prunable` and a scheduled `model:prune`. Read the window as configured and branch on it. Zero or null means keep, and the pruner must do nothing:

```php
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Prunable;

final class LoginAttempt extends Model
{
    use Prunable;

    public function prunable(): Builder
    {
        $days = config('security.login_attempts.retention_days');

        if (! is_int($days) || $days <= 0) {
            return static::query()->whereRaw('1 = 0'); // keep forever: a decision, not a missing value
        }

        return static::query()->where('created_at', '<', now()->subDays($days));
    }
}
```

Measure the cutoff to the second (`now()->subDays()`), not from the start of a day, which makes the real window depend on when the scheduler ran. Do not prune rows that something still relies on within their window: a webhook idempotency row deleted before the provider stops retrying turns a redelivery into a second application (see [idempotency](idempotency.md)). The log files need the same decision: the `daily` log channel's `days` option is their retention.

## How to test it

```php
it('logs the order id, not the order', function () {
    $log = Log::spy();
    $order = Order::factory()->create();

    app(PlaceOrder::class)->handle($order);

    $log->shouldHaveReceived('info')->withArgs(
        fn (string $message, array $context = []) => $context === ['order_id' => $order->id, 'total_cents' => $order->total_cents],
    );
});

it('prunes nothing when retention is switched off', function () {
    config(['security.login_attempts.retention_days' => 0]);
    LoginAttempt::factory()->create(['created_at' => now()->subYears(2)]);

    $this->artisan('model:prune', ['--model' => [LoginAttempt::class]]);

    expect(LoginAttempt::query()->count())->toBe(1);
});
```

Put `['order' => $order]` back in the log call, or clamp the window with `max(1, ...)`, and the matching test goes red.

## Check

`NoPayloadInLogRule` (in `extension.neon`) reports a `Log::emergency()` to `Log::debug()` call whose message or context is an Eloquent model, `all()` or `input()` called with no arguments on a request (or `request()`), or a whole `Request`. It also reports those values placed directly in the context array. The message ends with `See laravel-pitfalls: pii-logs`. Ids, scalar fields and `input('key')` are not reported.

What it cannot see, and review has to: a payload passed through a variable, `$model->toArray()`, `Log::log()` and channel loggers, exception context, audit payloads, and retention. Those are review items.
