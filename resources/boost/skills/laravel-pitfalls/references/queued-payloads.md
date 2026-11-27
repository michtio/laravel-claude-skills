# Queued payloads: what a queued listener, job or notification carries

Gap: covered partly by Boost (laravel-best-practices, rules/events-notifications.blade.php: "Queue slow notifications"; "Implement `HasLocalePreference` on notifiable models")

Boost says to queue slow notifications and to give notifiable models a preferred locale. It does not say what a queued payload holds once it leaves the request: the serialized models, the secrets in clear, or the locale the worker renders in. Every queued listener, job and notification is written to the queue backend (`jobs` on the database driver, Redis, SQS) and, when it fails, to `failed_jobs`.

## Pitfall 1: a queued listener serializes the full user

An event that carries the user model is serialized into the payload of every queued listener on it. With `SerializesModels` on the event (Laravel's `Login` and `Registered` and the laravel/passkeys events use it) only the model's class and key travel, and the worker reloads the user, as it is then. Without it, PHP serializes the whole model with every attribute: a queued listener on a third-party event that does not use `SerializesModels` writes the user's password hash and remember token into the queue and `failed_jobs`, whatever `$hidden` says.

- Read the event class before you queue a listener on it. When it carries the user without `SerializesModels`, never queue listeners on it: do the slow part in a job you dispatch with the user's id only.
- Or wrap the user in a non-serializable adapter holding only the fields the listener needs, so a queued listener cannot carry the password hash or remember token.
- With `SerializesModels`, the reloaded user may have changed or been deleted by the time the worker runs: a listener that needs the state at sign-in time copies those fields into its own job.

## Pitfall 2: a queued secret sits in clear in the queue

A queued notification is serialized with its public properties and the notifiable's routes. A package that stores only hashes of its tokens still leaves the raw token, the code and the address in the queue until the job is deleted, and a failed job keeps them in `failed_jobs`.

- A queued job or notification that carries a secret (a token, a one-time code, a magic link) implements `ShouldBeEncrypted`: the queue encrypts the payload, and `SendQueuedNotifications` copies the flag from the notification.
- A "we store only hashes" claim is checked against the queue payload and `failed_jobs`, not only the package's own table.
- Mark secret parameters `#[\SensitiveParameter]`, so a stack trace in the log never shows them.
- A sync queue sends inline: "queued" in a test on the sync connection proves nothing about when or where it runs.

## Pitfall 3: a queued notification renders in the worker's locale

A queued notification without its locale is rendered in the worker's locale, not the one active when it was sent: the sender takes the notification's `locale`, then the notifiable's `HasLocalePreference`, and never `app()->getLocale()` of the request.

- Set `->locale(app()->getLocale())` on every queued notification that must render in the request's language, or implement `HasLocalePreference` on the notifiable.
- Test it by reading the fake's recorded locale: `NotificationFake` records `locale` only from the notification, the fake's own locale or `HasLocalePreference`, so a test that sends under `nl` sees `null` unless the code sets it. Rendering the notification under the current locale proves nothing.

```php
Notification::fake();
app()->setLocale('nl');

app(SendSignInLink::class)->handle($user);

Notification::assertSentTo($user, SignInLink::class, function (SignInLink $notification, array $channels, object $notifiable, ?string $locale) {
    return $locale === 'nl';
});
```

## How to test it

- Payloads: dispatch with the database queue in the test, read the `jobs` row's payload, and assert that the raw token and the password hash are absent (an encrypted payload holds neither).
- Locale: as above, through the fake's recorded locale.

## Check

Review only. For every queued listener, job or notification, read what it carries: an event with a user, a secret, an address.
