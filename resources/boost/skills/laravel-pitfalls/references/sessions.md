# Sign-in and sessions: remember me, password confirmation, lookups by address

Gap: not covered by Boost

Boost's skills say nothing about what Laravel's session guard does on a remember-me sign-in, how `password.confirm` decides, what a session key written by a package means to the framework, or how a lookup by address matches under a database collation. Each item below is a Laravel 13 behavior that a correct-looking sign-in feature trips over.

## Pitfall 1: Login fires for remember-me cookies

`SessionGuard::user()` signs a user in from the recaller cookie and fires `Login` with `viaRemember()` true. A listener that treats `Login` as a fresh sign-in (a recent-auth stamp, a new-device alert, a "welcome back" mail) runs for every cookie sign-in too: such a fresh-sign-in listener checks the guard's `viaRemember()` and returns early on a remember-me cookie, or listens to its own event fired from the login form.

- A remember-me sign-in keeps the guest session's data: `user()` calls `updateSession()`, which regenerates the session id and keeps its contents, so a value written to the guest session (a code consumed before the sign-in, a stamp) is honored for whichever member the cookie signs in. Bind such a value to its member and clear it on every `Login` event for anyone else, the remember path included.
- Test it with a second member's remember cookie on the stamped session: the stamp must be gone after that sign-in.

## Pitfall 2: password.confirm honors one global timeout

- The `password.confirm` middleware (`RequirePassword`) honors `auth.password_timeout`, 3 hours by default (10800 seconds), and reads only the session key `auth.password_confirmed_at` by time.
- So anything that writes `auth.password_confirmed_at` (a passkey or code confirmation calling `passwordConfirmed()`) silences confirmation for the global timeout, not for the caller's own shorter window. Pass the window per route (`password.confirm:,600` or `RequirePassword::using(null, 600)`), or keep your own stamp.
- A package that writes a framework session key read without the package's own binding (`auth.password_confirmed_at`, the intended URL, the locale) guards the write of that session key by who is signed in: never write it when a different member is signed in than the one who confirmed. Guard the writer, not the reader, and test it with a second member signed in.
- During a `Login` event the guard may still hold the previous user (an account switch in one request), so the Login path needs its own unconditional write or clear; and with both a central and a caller-side guard, give each its own test, because the gate stays green with either one removed.

## Pitfall 3: revoking one device's remember-me

- `SessionGuard::logout()` cycles the user's single `remember_token`, which kills the remember-me cookie on every device the user has.
- `logoutCurrentDevice()` does not cycle the remember token: it clears this session and this device's recaller cookie only.
- Laravel has one `remember_token` per user, so per-device revocation needs its own binding: a companion cookie named after `getRecallerName()` plus a suffix, with the recaller's expiry, path, domain and SameSite, holding a random secret whose hash sits on the device's row.
- Refuse a revoked device in a `Login` listener: on `viaRemember()`, when the companion cookie does not match a live device, call `logoutCurrentDevice()`. The guard sets its user before it fires `Login` and returns that property afterwards, so the call leaves `user()` returning null and the request stays a guest. Keep a middleware as the second line only: an opt-in middleware leaves every route without it open (pitfall 4).
- In that listener, tell the remember path apart with `viaRemember() && getUser() === $event->user`: `viaRemember()` stays true after a failed recaller (the token matched, the password hash in the cookie did not), so `viaRemember()` alone is not proof that this sign-in came from the cookie.

## Pitfall 4: an opt-in middleware that records state when it finds none

A per-route middleware that enforces state and records it when missing ("signed in before the feature existed, record this device now") is bypassed by one request on a route without it. There the remember-me sign-in goes unrefused and the session stores the login id; on the next request, to a covered route, `viaRemember()` is false and the middleware records a fresh live device for a revoked one.

- Trace two requests: first an uncovered route (a Sanctum stateful API route, a `withoutMiddleware` route, a public page), then a covered one. Treat every "record when missing" branch as fail-open until a test of that sequence proves otherwise.
- Enforce at the sign-in itself (the `Login` listener above) or in global middleware, and keep the per-route middleware as a second line.

## Pitfall 5: a lookup by address matches a different address

`User::where('email', $input)` on MySQL matches under the column's collation. Laravel's default `utf8mb4_unicode_ci`, MySQL 8's `utf8mb4_0900_ai_ci` and `utf8mb4_general_ci` are case- and accent-insensitive collations; the PAD SPACE ones also ignore trailing spaces. `bob@exämple.com` finds `bob@example.com`.

- After a lookup by address, mail the stored address (`$user->email`), never the input: Laravel's password broker mails `getEmailForPasswordReset()`, the stored one. Treat a row whose stored address differs from the normalized input as not found.
- Key throttles on the matched record's key as well as the input, or one account has unlimited throttle keys.
- Compare identifiers that must match strictly (an origin, a token key, a case-sensitive code) in PHP with `hash_equals`, or give the column a binary collation (`->collation('utf8mb4_bin')`, MySQL only): a strict `where` on a `_ci` column is not strict.

## Pitfall 6: a secret derived from APP_KEY

- Derive a per-purpose secret from APP_KEY with HMAC and a fixed label (`hash_hmac('sha256', 'magic-link|'.$payload, $key)`), a domain-separation prefix so one derived value never equals another purpose's.
- Length-prefix or JSON-encode the inputs before hashing: joining `morph:key` parts with `:` collides when a part holds the separator (`a:b` + `c` against `a` + `b:c`).
- `APP_PREVIOUS_KEYS` rotation helps decryption only: a value derived from APP_KEY ignores the previous keys, so rotating the key kills every live derived value. Say so in the docblock.
- A changed morph map changes every value derived from the morph alias: derive from something stable, or treat a morph map change as a rotation.

## Pitfall 7: laravel/passkeys (pre-1.0)

`laravel/passkeys` 0.x facts a consumer relies on, read from its source at tag v0.3.0 (repository `laravel/passkeys-server`); recheck them at each minor (see its register row):

- Its actions take a `PasskeyUser` contract: the user model implements `PasskeyUser` (the package's trait helps), or the actions do not accept it.
- `Passkeys::userModel()` drives the migration's foreign key (`foreignIdFor(Passkeys::userModel())`, default `App\Models\User`): set it before the migration runs.
- Synced passkeys (platform password managers) report a signature counter of 0 on every use, so the counter check cannot catch a replay or a cloned credential.
- Its actions store no challenge: the bundled routes keep the options in the session and pull them, but when your app calls the actions itself, single use of the options is your app's job.
- Its passkey management routes use `password.confirm` by default (`passkeys.management_middleware`), with the global timeout of pitfall 2, and its events (`PasskeyVerified`, `PasskeyRegistered`) carry the full user model, so a queued listener serializes it (see [queued payloads](queued-payloads.md)).

## How to test it

- Remember me: a feature test that sets the recaller cookie with `withCredentials()` (JSON helpers send no cookies otherwise; see [testing](testing.md)) and asserts the listener's effect, once for a fresh sign-in and once for the cookie.
- Revocation: revoke a device, send its recaller and companion cookies to a route with and without the middleware, and assert a guest each time; then send a covered request after an uncovered one.
- Lookups by address: on MySQL, look up with an accent-changed and an upper-cased address and assert the mail goes to the stored address.

## Check

Review only.
