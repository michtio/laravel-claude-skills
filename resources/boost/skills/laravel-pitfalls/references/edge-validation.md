# Edge validation: input the framework accepts and should not

Gap: covered partly by Boost (laravel-best-practices, rules/config.blade.php: "Read environment variables in configuration files")

Boost covers the rule that `env()` belongs in config files. It does not cover what happens to the value on the way in: a cast that turns a missing variable into zero, a LIKE pattern that treats the user's `%` as a wildcard, or a reference id that passes validation for a row the user may not touch. Each of these is input that Laravel and the database accept without complaint. This reference adds checks for the first three.

## Pitfall 1: env() outside config

Once `php artisan config:cache` has run, Laravel stops loading `.env`, and `env()` returns null (or its default) anywhere outside the config files. The code works locally and in tests, then reads null in production. The rule is Boost's. What this package adds is a check that enforces it.

### Fix

Read the variable in a config file and use `config()` everywhere else:

```php
// config/services.php
'payments' => ['key' => env('PAYMENTS_KEY')],

// application code
$key = config('services.payments.key');
```

## Pitfall 2: a cast on env()

```php
'timeout' => (int) env('PAYMENTS_TIMEOUT'),    // unset: 0, "30s": 30, "abc": 0
'rate'    => (float) env('FX_MARGIN'),         // unset: 0.0
'verify'  => (bool) env('PAYMENTS_VERIFY_TLS'), // unset: false, TLS verification off
```

`env()` returns strings (it maps only `true`, `false`, `null` and `empty`), so people cast. The cast accepts anything: a missing or mistyped variable becomes `0`, `0.0` or `false`, and the application starts with a zero timeout or with verification turned off instead of failing at boot.

### Fix

Give `env()` a default, convert strictly so a malformed value becomes null instead of zero, and read it through a typed accessor (`config()->integer()`, `config()->float()`, `config()->boolean()`). The accessor throws when the value is not of that type:

```php
// config/services.php
'payments' => [
    'timeout' => filter_var(env('PAYMENTS_TIMEOUT', 30), FILTER_VALIDATE_INT, FILTER_NULL_ON_FAILURE),
    'verify_tls' => env('PAYMENTS_VERIFY_TLS', true),
],

// application code: throws on null or a string instead of running with 0
$timeout = config()->integer('services.payments.timeout');
$verify = config()->boolean('services.payments.verify_tls');
```

For a variable that has no safe default, `Env::getOrFail('PAYMENTS_KEY')` in the config file throws when it is unset.

## Pitfall 3: an unescaped LIKE pattern

```php
User::query()->where('email', 'like', '%'.$request->input('q').'%')->get();
```

Bindings prevent SQL injection, but LIKE wildcards are not escaped. A search for `%` returns every row, a search for `_` matches any single character, and a "starts with" filter on an account prefix matches other accounts too.

### Fix

Escape `\`, `%` and `_` before building the pattern:

```php
$term = addcslashes($request->string('q')->toString(), '\\%_');

User::query()->whereLike('email', '%'.$term.'%')->get();
```

MySQL, MariaDB and PostgreSQL use backslash as the default LIKE escape character. SQLite has no default escape character, so on SQLite the escaped pattern needs an `ESCAPE '\'` clause (`whereRaw("email like ? escape '\\'", [$pattern])`). It also means a test run on SQLite does not prove the escaping works on the production engine.

## Pitfall 4: a reference id that exists, but not for this user

`'client_id' => 'exists:clients,id'` passes for every client in the table, including those of other tenants. The foreign key passes too. See [authorization](authorization.md), pitfall 3: constrain the rule with `Rule::exists(...)->where(...)` or resolve the id through the scoped model. Related: an unknown id that the code silently ignores (an optional tax rate, a discount code) changes the result without any error. Refuse ids that do not resolve. Treating them as absent hides the mistake.

## How to test it

- Env and casts: the checks below are the tests. Add a boot-time test that calls `config()->integer('services.payments.timeout')` with the variable set to `abc` and expects an exception. Restore the `(int)` cast and it returns 0 instead.
- LIKE, run on the production database engine:

```php
it('treats a percent sign as a literal', function () {
    User::factory()->create(['email' => 'ann@example.test']);
    User::factory()->create(['email' => '100%@example.test']);

    $found = app(UserSearch::class)->byEmail('%');

    expect($found->pluck('email')->all())->toBe(['100%@example.test']);
});
```

Remove `addcslashes()` and the test goes red: both users match.

## Check

Three rules in `extension.neon`, each ending `See laravel-pitfalls: edge-validation`:

- `NoEnvOutsideConfigRule` reports every `env()` call in a file with no `config` directory segment in its path. Proof: `tests/PHPStan/Rules/NoEnvOutsideConfigRuleTest.php`. Larastan 3 has an equivalent check, on by default (`noEnvCallsOutsideOfConfig`), so a Larastan project sees this error twice. This one is for projects that run PHPStan without Larastan.
- `NoCastOnEnvRule` reports an `(int)`, `(float)` or `(bool)` cast applied directly to `env()`. Proof: `tests/PHPStan/Rules/NoCastOnEnvRuleTest.php`.
- `NoUnescapedLikeRule` reports `where()` and `orWhere()` with a `like` operator, and the `whereLike()` family, when the pattern is a concatenation or an interpolated string that has a part not wrapped in `addcslashes()`, `str_replace()` or an `escapeLike()` method. Proof: `tests/PHPStan/Rules/NoUnescapedLikeRuleTest.php`. A pattern passed as a bare variable is not judged, because that needs data flow.

Pitfall 4 is a review item.
