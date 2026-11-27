# Concurrency: check then act

Gap: covered partly by Boost (laravel-best-practices, rules/architecture.md: "Use atomic locks for race conditions")

Boost says to take a lock (`Cache::lock()` or `lockForUpdate()` inside a transaction) when processes must not overlap. It does not say what has to happen after the lock is taken, and that is where this bug lives: the guard still reads data from before the lock.

## The pitfall

A method decides whether it may write by asking a model it was handed, then writes:

```php
public function writeOff(Invoice $invoice): void
{
    if ($invoice->status !== 'open') {
        throw new InvoiceNotOpen();
    }

    DB::transaction(function () use ($invoice) {
        $invoice->update(['status' => 'written_off', 'written_off_cents' => $invoice->balance_cents]);
    });
}
```

`$invoice` reflects the row as it was when the request loaded it, and often as it was when someone opened the page minutes earlier. Between that read and the write, another request can change the row:

- a payment lands, and the write-off clears a balance that was already paid;
- a send posts the document, and an edit then rewrites something that was already posted;
- two open tabs both convert one quote, and both pass every guard.

Adding `lockForUpdate()` somewhere does not fix this if the guard and the amounts still come from the model that was passed in. The lock protects only the row that was actually read under it.

## Why it bites

Every automated check stays green. Each request is correct on its own, unit tests run one request at a time, and a database constraint rarely covers "may only happen while open". The failure needs two requests close together, which in production comes from a double-click, a retried request, or two people on the same record.

## The fix: lock, re-read, recheck

Open the transaction, re-read the row `FOR UPDATE`, run every guard against the locked row, and take every amount from it. If the guard fails because the work is already done, return without doing anything, so a double-click does nothing instead of failing.

```php
use App\Models\Invoice;
use Illuminate\Support\Facades\DB;

public function writeOff(Invoice $invoice): void
{
    DB::transaction(function () use ($invoice) {
        $locked = Invoice::query()
            ->whereKey($invoice->getKey())
            ->lockForUpdate()
            ->firstOrFail();

        if ($locked->status === 'written_off') {
            return; // already done: a repeat is a no-op
        }

        if ($locked->status !== 'open' || $locked->balance_cents === 0) {
            throw new InvoiceNotOpen();
        }

        $locked->update([
            'status' => 'written_off',
            'written_off_cents' => $locked->balance_cents,
        ]);
    });
}
```

Put the re-read in one place (a `lockedInvoice($id)` helper on the service) so every state-changing method uses the same one. When a method locks more than one row, always lock them in the same order (for example by primary key) to avoid deadlocks.

### Counters: increment in SQL, never read-modify-write

`$order->amount_paid_cents += $cents; $order->save();` is the same race in one line: two payments read the same old total and one is lost. Let the database do the arithmetic:

```php
$order->increment('amount_paid_cents', $cents);
```

When the new value is needed afterwards, read it from the locked row in the same transaction. Do not compute it in PHP from a value read before the lock.

### Once per period: the database has the last word

A rule like "one renewal invoice per subscription per period" needs a unique index (`unique(['subscription_id', 'period_start'])`). Lock the parent row and re-read its cursor from the locked row, then advance the cursor and create the child in the same transaction. A queue-level guard (`ShouldBeUnique`, `Cache::lock()`) stops the work from being attempted twice, but it does not stop it from being done wrong: a second worker, a manual retry or a scheduler overlap gets past it. The index is the guard that cannot be skipped.

## How to test it

Real concurrency is hard to stage in a test. A stale model is easy to stage, and it is exactly what the fix guards against: load the model, change the row underneath it, then call the method with the stale instance.

```php
it('does not write off an invoice that was paid after it was loaded', function () {
    $invoice = Invoice::factory()->create(['status' => 'open', 'balance_cents' => 5000]);
    $stale = Invoice::query()->findOrFail($invoice->id); // what the open screen holds

    // A payment lands in another request.
    Invoice::query()->whereKey($invoice->id)->update(['status' => 'paid', 'balance_cents' => 0]);

    expect(fn () => app(InvoiceService::class)->writeOff($stale))->toThrow(InvoiceNotOpen::class);
    expect($invoice->fresh()->status)->toBe('paid');
});

it('treats a repeated write-off as a no-op', function () {
    $invoice = Invoice::factory()->create(['status' => 'open', 'balance_cents' => 5000]);
    $stale = Invoice::query()->findOrFail($invoice->id);

    app(InvoiceService::class)->writeOff($invoice);
    app(InvoiceService::class)->writeOff($stale); // the second click

    expect($invoice->fresh()->written_off_cents)->toBe(5000);
});
```

Revert the fix (guard on `$invoice` instead of `$locked`) and the first test goes red: the write-off goes through on a paid invoice.

## Check

No static check. Whether a guard reads the locked row or the passed-in model depends on data flow, which a lexical rule cannot see reliably. It is a review item: for every method that changes state, find the guard and confirm it reads a row fetched with `lockForUpdate()` inside the same `DB::transaction()`.
