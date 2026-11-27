# Debugger fixture: two causes

Not a real app. `tests/Feature/InvoiceTotalTest.php` is red because of two independent causes, in two files: the coupon discount is computed with an integer cast that truncates `0.15` to `0` (`app/Services/DiscountCalculator.php`), and the invoice sums the lines with `withTrashed()`, so a line the customer removed is still counted (`app/Services/InvoiceCalculator.php`). Fixing either one alone leaves the test red with the other's message. `vendor/bin/pest` is an sh stand-in (see `CLAUDE.md`).
