<?php

use App\Services\InvoiceCalculator;

// Order 42: one line of 5000 cents (kept), one line of 3000 cents (removed by the customer,
// so soft deleted), and a 15 percent coupon. The invoice must total 4250.
it('totals an order with a coupon and a removed line', function () {
    // expect-absent: app/Services/DiscountCalculator.php (int) ($coupon->percent / 100) => discount for a subtotal of 5000 is 0, expected 750
    // expect-absent: app/Services/InvoiceCalculator.php withTrashed() => the invoice counts 2 lines, expected 1
    expect(app(InvoiceCalculator::class)->total(Order::findOrFail(42)))->toBe(4250);
});

it('totals an order without a coupon', function () {
    // expect-file: app/Services/InvoiceCalculator.php
    expect(app(InvoiceCalculator::class)->total(Order::findOrFail(7)))->toBe(5000);
});
