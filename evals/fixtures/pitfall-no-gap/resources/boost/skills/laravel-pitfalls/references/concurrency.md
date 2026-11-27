# Concurrency

## Check then act

Reading a row and then writing based on what was read lets two requests pass
the same check. Lock the row and recheck after taking the lock.

```php
DB::transaction(function () use ($id) {
    $order = Order::query()->lockForUpdate()->findOrFail($id);

    if ($order->status !== 'pending') {
        return;
    }

    $order->update(['status' => 'paid']);
});
```
