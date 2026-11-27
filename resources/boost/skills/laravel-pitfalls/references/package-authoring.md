# Writing a package: dependencies, providers, framework internals and pruning

Gap: not covered by Boost

Boost's skills are written for applications. A package runs inside apps it has never seen, so mistakes that an app gets away with (a missing dependency, a schedule entry nobody adds, a reach into a framework internal) only show up in someone else's project. Each item here is a decision a package builder had to make alone.

## Pitfall 1: the package rules an app never needs

- Declare every `illuminate/*` component the package touches in `require` (`illuminate/database` for Eloquent, `illuminate/support` for facades and the container), with the Laravel majors it supports; never lean on `laravel/framework` arriving through the app.
- A library does not commit `composer.lock`: the consuming app resolves the versions, and a committed lock only hides what the package's own CI should test against.
- In the service provider, register binds and merges config, boot reads config and wires routes, views, commands and schedules: never resolve another service or read config in `register`, where providers that load later have not bound theirs yet.
- Validate the package config at boot and fail with a message that names the key, so a wrong value stops the app at start instead of failing later in a request.
- Make the package's service providers final: an app configures the package through config and events, never by extending the provider.
- Publishable files carry publish tags (`$this->publishes([...], 'yourpackage-config')`), so an app publishes the config without the migrations.
- Code against contracts and the container, never against the app's own classes or `App\` names.

## Pitfall 2: tagged services that can fail to resolve

`Container::tagged()` stops at the first abstract that throws: its generator resolves each tagged abstract in turn, so one sink whose dependency is missing silently drops every later one. Laravel 13 also has no public list of a tag's abstracts: the map is a protected property, and the contract only has `tagged()`.

- Instead: a registry the provider fills through an explicit `register()` method (`$registry->register(SlackSink::class)`), which can resolve each entry on its own and report the one that fails.
- Or wrap each tagged resolution in a lazy closure at tag time, so resolving one entry never runs the others.

## Pitfall 3: a reach into a framework internal

When there is no public API and the package must read a protected property, guard it the honest way:

- Read it by reflection after a `ReflectionClass::hasProperty()` check, with a fallback to the public API when the property is gone, and a canary test that fails when the framework changes the internal.
- Never `?? []` on the property: that is the silent fallback that hides a rename in a minor release, and `property_exists` there trips PHPStan's narrowing rules.
- On an unexpected shape (the property exists but holds something else), fall back to the public API as on a missing property, or return null, and log once: a filter that returns an empty list on a changed shape drops every entry with no fallback and no log.

```php
private function tagMap(Container $container): ?array
{
    $class = new ReflectionClass($container);

    if (! $class->hasProperty('tags')) {
        return null; // gone: use the public API
    }

    $map = $class->getProperty('tags')->getValue($container);

    if (! is_array($map) || ! array_is_list($map[self::TAG] ?? [])) {
        if (! self::$shapeWarned) {
            self::$shapeWarned = true; // log once per process
            Log::warning('Container tag map has an unexpected shape; using tagged().');
        }

        return null;
    }

    return $map;
}
```

## Pitfall 4: a Testbench script that throws exits 0

A PHP script that boots Testbench's `Application::create()` and then throws still exits with status 0: the framework's exception handler renders the exception for the console and does not set a failing exit code. A parent test that checks only the exit code sees a pass.

- Wrap the script's work in `try { ... } catch (Throwable $e) { fwrite(STDERR, $e->getMessage()); exit(1); }`.
- The parent requires a result marker (a `RESULT:` line the script prints last), never only the exit code.

## Pitfall 5: a package model nobody prunes

`model:prune` without `--model` only discovers the app's own models in `app/Models`, never a package's Prunable model, so expired rows stay forever unless every consumer remembers the flag.

- The package schedules `model:prune --model=...` for its own Prunable models itself (from its provider, with `callAfterResolving(Schedule::class, ...)`), or documents the schedule entry as a required install step.
- A gate that calls `model:prune --model=...` directly passes either way: it does not prove a real app prunes the model.

## How to test it

- Dependencies: a CI job that installs the package with `--prefer-lowest` against each supported Laravel major.
- Tagged services: register one sink that throws, and assert the others still receive the event.
- Reach-ins: a canary test that subclasses the framework class and asserts the property and its shape; a second test that removes it and asserts the public API path runs.
- Pruning: boot the package in Testbench, resolve the `Schedule`, and assert an event for `model:prune` with `--model` naming the package's model.

## Check

Review only.
