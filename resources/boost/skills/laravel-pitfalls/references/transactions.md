# Transactions: boundaries and side effects

Gap: covered partly by Boost (laravel-best-practices, rules/mail.md: "Dispatch queued mail after commit"; rules/events-notifications.md: "Use ShouldDispatchAfterCommit inside transactions")

Boost covers queued mail, queued notifications and events: mark them after-commit so a rollback discards them. It also notes that this does not defer synchronous delivery. It does not cover what that leaves out: outbound HTTP and synchronous mail written inside the transaction, `DB::afterCommit()`, or the opposite mistake, where work that must succeed or fail together is split across transactions.

## Pitfall 1: a side effect inside the transaction

```php
DB::transaction(function () use ($order, $customer) {
    $order->update(['status' => 'paid']);
    $order->lines()->update(['locked' => true]);

    Http::post('https://fulfilment.example/orders', ['id' => $order->id]); // cannot be rolled back
    Mail::to($customer)->send(new OrderPaid($order));                      // sent even if we roll back

    $order->customer->increment('lifetime_cents', $order->total_cents);    // may throw: deadlock, constraint
});
```

### Why it bites

- The database rolls back. The HTTP request and the mail do not. If anything after them throws, the warehouse ships an order that is not paid, and the customer has a receipt for it.
- The network call runs while the row locks are held. A slow provider stalls every request waiting on those rows, and a timeout throws inside the transaction and rolls back a write that was fine.
- Deadlock retries make it worse: `DB::transaction($callback, 3)` runs the closure again, so the request and the mail go out again on every attempt.

### The fix

Do the side effect after the commit. Either move it below the transaction, or, when it is decided deep inside the transaction, register it with `DB::afterCommit()`. The callback runs only once the outermost transaction commits, and is dropped when it rolls back:

```php
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Mail;

DB::transaction(function () use ($order, $customer) {
    $order->update(['status' => 'paid']);
    $order->lines()->update(['locked' => true]);
    $order->customer->increment('lifetime_cents', $order->total_cents);

    DB::afterCommit(function () use ($order, $customer) {
        Http::post('https://fulfilment.example/orders', ['id' => $order->id]);
        Mail::to($customer)->send(new OrderPaid($order));
    });
});
```

For queued work, call `->afterCommit()` on the job (`NotifyFulfilment::dispatch($order->id)->afterCommit()`) or set `after_commit` on the queue connection. A side effect that is allowed to fail without undoing the write (email, search sync, a notification) belongs in a queued listener dispatched after commit, so a failure of its own does not reach the request.

Outside any transaction, `DB::afterCommit()` runs the callback straight away, so the same code is safe when called from a path that has not opened a transaction.

## Pitfall 2: one change split across transactions

The opposite mistake: steps that must succeed or fail together run in separate transactions, or one of them is moved into an event listener to "decouple" it.

```php
DB::transaction(fn () => $customer->decrement('credit_cents', $amount));      // committed
DB::transaction(fn () => $invoice->payments()->create(['amount_cents' => $amount])); // throws
```

The credit is spent and the payment it paid for is gone. The books still balance, and no routine check notices. The same happens when a write that must be posted together with the document is turned into an event: if the listener fails, the document stays without its posting.

### The fix

Do every step of the change inside one `DB::transaction()`, as direct synchronous calls. An event or queued listener is for side effects that may fail on their own, never for a write the change depends on.

```php
DB::transaction(function () use ($customer, $invoice, $amount) {
    $customer->decrement('credit_cents', $amount);
    $invoice->payments()->create(['amount_cents' => $amount, 'source' => 'credit']);
    $invoice->increment('amount_paid_cents', $amount);
});
```

Take document numbers inside the transaction that creates the document, with one atomic statement. A number taken before the transaction is lost when the transaction fails, and leaves a gap in the sequence.

## How to test it

Fake the side effect, make the transaction fail after the point where the call is made, and assert nothing went out:

```php
it('sends nothing to fulfilment when the payment rolls back', function () {
    Http::fake();
    Mail::fake();
    $order = Order::factory()->create(['total_cents' => 5000]);
    Customer::updating(fn () => throw new RuntimeException('simulated deadlock')); // the increment fails

    expect(fn () => app(Checkout::class)->markPaid($order))->toThrow(RuntimeException::class);

    Http::assertNothingSent();
    Mail::assertNothingSent();
    expect($order->fresh()->status)->not->toBe('paid');
});
```

Move the `Http::post()` back inside the transaction, ahead of the failing step, and the test goes red. This works with `RefreshDatabase`: Laravel's testing transaction manager ignores the test's own wrapping transaction, so `DB::afterCommit()` callbacks run when the application's transaction commits, and are dropped when it rolls back.

For pitfall 2, force the second step to throw and assert the first step's change is gone (`expect($customer->fresh()->credit_cents)->toBe($before)`).

## Check

`NoSideEffectInTransactionRule` (in `extension.neon`) reports every `Http::` or `Mail::` facade call written inside a closure or arrow function passed to `DB::transaction()`, nested closures included, except inside `DB::afterCommit()`. The message ends with `See laravel-pitfalls: transactions`. Its proof is `tests/PHPStan/Rules/NoSideEffectInTransactionRuleTest.php`: the bad fixture must report each call on its line, and the good fixture (after the transaction, in `DB::afterCommit()`, queued `->afterCommit()`) must report nothing.

What the rule cannot see, and review has to: a side effect inside a method that the closure calls, the `DB::beginTransaction()` ... `DB::commit()` form, and pitfall 2.
