# Idempotency: webhooks and providers

Gap: covered partly by Boost (laravel-best-practices, rules/http-client.md: "Retry only safe operations"; rules/queue-jobs.md: "Use unique jobs for dispatch deduplication")

Boost covers the outgoing side (send an idempotency key when you retry a state-changing request) and notes that a unique job does not replace idempotent processing or a database constraint. It does not cover the incoming side: how to make applying a webhook idempotent, where to record that an event was handled, or why the event id alone is not enough.

A provider has already moved money (or shipped, or cancelled) by the time the application hears about it. The failure is not a refused write. It is that the application's records no longer match what actually happened.

## Pitfall 1: the "already processed" record is committed apart from the work

Providers deliver at least once, so every handler records which events it has handled. The bug is where that record is written:

- **Recorded first, committed on its own.** The event is marked handled, then applying it fails and rolls back. The next delivery is skipped as a duplicate, and the payment is never recorded. Providers stop retrying after they get a 2xx response or run out of attempts, so the event will not come back.
- **Recorded last, in a separate step.** The work commits, the process dies before the marker is written, and the retry applies the payment a second time.

### The fix: insert the event row first, inside the same transaction

Give the event table a unique key on the provider event id, and insert into it as the first statement of the transaction that applies the event. A duplicate delivery hits the key before anything else happens. A failure rolls the row back together with the work, so the next delivery finds the event unprocessed.

```php
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

Schema::create('processed_webhook_events', function (Blueprint $table) {
    $table->id();
    $table->string('provider');
    $table->string('event_id');
    $table->timestamps();

    $table->unique(['provider', 'event_id']);
});
```

```php
use Illuminate\Support\Facades\DB;

public function handle(array $event): void
{
    DB::transaction(function () use ($event) {
        $inserted = DB::table('processed_webhook_events')->insertOrIgnore([
            'provider' => 'payments',
            'event_id' => $event['id'],
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        if ($inserted === 0) {
            return; // a redelivery of an event already applied
        }

        $this->applyPayment($event); // same transaction: fails together with the row above
    });
}
```

`insertOrIgnore()` returns the number of rows inserted and does not abort the transaction on a duplicate (a plain insert that hits the key would abort it on PostgreSQL). Record failures separately, after the rollback, for example in a `failed_webhook_events` table or the log, so an event that fails on every delivery shows up somewhere.

## Pitfall 2: event idempotency is not provider idempotency

One real-world change can arrive as several events with different ids. A paid invoice often produces both an "invoice paid" event and a "payment succeeded" event, and a refund made in the provider's dashboard arrives as a webhook for a refund the application may have already recorded itself. The event table can only collapse duplicate deliveries of the same event, so here the same payment gets recorded twice.

### The fix: a unique key on the provider's own object id

Store the provider's id for the thing itself (payment id, refund id, charge id) on the row the event creates, with a unique index, and write it so a second arrival finds the first:

```php
$table->string('provider_payment_id')->unique();
```

```php
$payment = Payment::query()->createOrFirst(
    ['provider_payment_id' => $event['data']['payment_id']],
    ['invoice_id' => $invoiceId, 'amount_cents' => $event['data']['amount']],
);
```

`createOrFirst()` relies on that unique index: it inserts inside a savepoint and, on a unique violation, returns the existing row. Without the index it inserts a duplicate. `firstOrCreate()` reads before it writes, which is the check-then-act race from [concurrency](concurrency.md).

The same key fixes outgoing calls. For a refund, call the provider first, then record the refund under the provider's refund id. If the process dies between the two, the provider's refund webhook records it later. Recording first would leave a refund on the books that the provider never made.

## How to test it

```php
it('applies a redelivered event once', function () {
    $event = paymentEvent(id: 'evt_1', paymentId: 'pay_1', amount: 5000);

    app(PaymentWebhook::class)->handle($event);
    app(PaymentWebhook::class)->handle($event);

    expect(Payment::query()->count())->toBe(1);
});

it('records one payment for two events about it', function () {
    app(PaymentWebhook::class)->handle(paymentEvent(id: 'evt_1', paymentId: 'pay_1', amount: 5000));
    app(PaymentWebhook::class)->handle(paymentEvent(id: 'evt_2', paymentId: 'pay_1', amount: 5000));

    expect(Payment::query()->count())->toBe(1);
});

it('leaves a failed event unprocessed so the next delivery applies it', function () {
    $event = paymentEvent(id: 'evt_1', paymentId: 'pay_1', amount: 5000, invoiceId: 999_999); // no such invoice

    expect(fn () => app(PaymentWebhook::class)->handle($event))->toThrow(Throwable::class);

    expect(DB::table('processed_webhook_events')->where('event_id', 'evt_1')->exists())->toBeFalse();
});
```

Each test goes red with its part of the fix reverted. Insert the event row in its own transaction and the third test fails. Drop the unique `provider_payment_id` (or use `create()`) and the second one fails. Remove the event row and the first one fails.

## Check

No static check. Which table guards which event, and whether its insert shares the transaction with the work, is design rather than syntax. It is a review item for every webhook handler: a unique key on (provider, event id) inserted first inside the applying transaction, and a unique key on the provider's object id on every row a provider event can create.
