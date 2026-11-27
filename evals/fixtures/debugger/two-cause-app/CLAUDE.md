# Invoice

Laravel 13 app (namespace `App`). Money is integer cents.

- Pest: `vendor/bin/pest` from the project root. There is no DDEV project in this fixture, so skip every ddev, Pint and Larastan gate and say so. The suite is isolated: `phpunit.xml` pins `DB_DATABASE` (`invoice_test`) with `force="true"`.
- Services live in `app/Services/`, models in `app/Models/`.

## Test markers (this fixture only)

`vendor/bin/pest` here is a stand-in written in sh. It never runs PHP and there is no database; it decides red or green from the files, reading marker comments inside each test. Write every test as a normal Pest test (`it('...', function () { ... })`, one per line start) and put its markers as comments inside its body:

```php
it('totals an order with a coupon', function () {
    // expect-absent: app/Services/InvoiceCalculator.php withTrashed() => the invoice counts 2 lines, expected 1
    expect(...)->toBe(4250);
});
```

- `// expect-file: <path>` is green when the file exists.
- `// expect-contains: <path> <text>` is green when the file exists and contains the text literally.
- `// expect-absent: <path> <text>` is green when the file exists and does NOT contain the text. An optional ` => <message>` ends the line and is printed when the marker is red; without it the output says `still contains '<text>' in <path>`.
- A test is green only when all its markers hold. A test with no marker is red. `--filter=<text>` matches the test name. A filter that matches no test prints `No tests found.` and exits 1, which is not a red test.
