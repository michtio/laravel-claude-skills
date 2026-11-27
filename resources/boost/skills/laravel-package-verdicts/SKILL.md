---
name: laravel-package-verdicts
description: Register of verdicts on common Laravel packages. Each verdict says whether to use a package, avoid it, or use it only under conditions, with a short factual reason and the date its Laravel support and maintenance were last checked. The project's own verdicts in .ai/skills-profile.json take precedence over the register.
when_to_use: Load before running composer require, before proposing a package in a plan, when reviewing a composer.json change or a dependency upgrade, and when asked which package to use for API or SPA authentication, OAuth, social login, permissions, billing, a frontend stack or admin panel, realtime, feature flags, queues dashboards, monitoring, debugging, data objects, settings, slugs, translations, media, PDFs, spreadsheets, search, backups, audit logs, static analysis or testing. Triggers on composer require, a new entry in composer.json, "which package", "is X still maintained", "does X support Laravel 13", a starter kit, Breeze, Jetstream, Volt, Sanctum vs Passport, Cashier, Livewire vs Inertia, Filament plugins, Octane, Reverb, Horizon, Telescope, Pulse, Debugbar, Larastan, Pest, deptrac.
---

# Laravel package verdicts

The register is [references/register.md](references/register.md): one row per package with its use, reason, conditions and the date it was last checked.

## Precedence

1. The project profile. Verdicts under the top-level `verdicts` key of `.ai/skills-profile.json` take precedence over the register, matched by package name. A profile entry replaces the register row for that package; packages only in the profile are added.
2. The register in this skill.
3. Neither has the package: it has no verdict yet. Treat it as `depends` and follow "A package with no verdict" below.

Read the profile first when it exists. Never tell the developer the register's verdict when the profile overrides it.

## Reading a verdict

- `use`: fine to add when the conditions hold. Still state the conditions in the plan or the change.
- `depends`: the conditions decide. Say which condition applies in this project and why; when that is unclear, ask before adding it.
- `avoid`: do not add it. If the developer asks for it or it is already in `composer.json`, cite the verdict's reason and the suggested alternative and ask for a ruling. Never remove a package on your own.

In a plan, cite the verdict as `<package>: <use> (<reason>)`. In a review, flag a package the register or profile says to avoid with that verdict's reason.

## A package with no verdict

Before proposing it, check and report:

- its latest stable release and date on Packagist, and whether its constraints allow the project's Laravel and PHP versions;
- whether the repository is archived or marked abandoned, and when it last had a release;
- whether Laravel or a package already in `composer.json` does the same job.

Then propose it and ask the developer for a ruling. A ruling worth keeping belongs in the project profile's `verdicts`, not in this register.

## Stale verdicts

A `Checked` date older than six months is a hint, not a verdict: recheck Laravel support and maintenance before relying on it, and say that you did.
