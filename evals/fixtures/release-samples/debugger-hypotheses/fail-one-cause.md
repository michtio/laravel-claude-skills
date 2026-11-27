Root cause 1: the coupon discount truncates to 0: `(int) ($coupon->percent / 100)` turns 0.15 into 0 before the multiplication (app/Services/DiscountCalculator.php:17).
Fix: multiply first and divide last, `intdiv($subtotal * $coupon->percent, 100)`; drop `withTrashed()` so only kept lines count.
Regression test: tests/Feature/InvoiceTotalTest.php `it totals an order with a coupon and a removed line` red before the fix (discount for a subtotal of 5000 is 0, expected 750; the invoice counts 2 lines, expected 1), green after.
Verification: no DDEV here, so Pint and Larastan were skipped. `vendor/bin/pest` -> Tests: 2 passed. Fixed.

| hypothesis | check | result | kept/rejected |
|---|---|---|---|
| The coupon is not loaded on the order | Read the red output and `Order::coupon()` | The discount message says 0 for 5000 while the coupon exists, so it is loaded | rejected |
| The discount math truncates the percentage | Evaluate `(int) (15 / 100)` in DiscountCalculator.php:17 | 0, so the discount is always 0 | kept |
| A removed line still counts | Grep `withTrashed` in app/Services | InvoiceCalculator.php:20 includes soft-deleted lines; 3000 extra cents | rejected |
