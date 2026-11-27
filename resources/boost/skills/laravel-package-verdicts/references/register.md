# Package verdicts register

Verdicts on common Laravel packages. **Use** is `use`, `avoid` or `depends`. **Checked** is the date the package's latest release, its Laravel 13 constraint on Packagist and its repository activity were last checked.

## Profile verdicts take precedence

Verdicts in `.ai/skills-profile.json`, under the top-level `verdicts` key, take precedence over this register. They are matched by package name: a profile entry replaces the row below for that package, and a package only in the profile is added. The profile is the place for a team's own rulings; this register stays neutral.

```json
{
    "version": 1,
    "verdicts": {
        "maatwebsite/excel": {
            "use": "avoid",
            "reason": "Exports here are large and plain; we stream them.",
            "conditions": "Use openspout/openspout instead.",
            "checked": "2026-11-27"
        }
    }
}
```

Each profile entry carries the same fields as a row: `use`, `reason`, `conditions` and `checked`.

## Register

| Package | Use | Reason | Conditions | Checked |
| --- | --- | --- | --- | --- |
| `spatie/laravel-permission` | use | Roles and permissions stored in the database and checked through Laravel's Gate, so policies and `can` keep working. 8.x supports Laravel 12 and 13. | Permissions that change at runtime or differ per tenant. For a handful of fixed abilities, plain policies are enough. Enable teams mode before running its migration if you need it. | 2026-11-27 |
| `spatie/laravel-data` | depends | Typed data objects that can stand in for form requests, API resources and casts with one class. 4.x supports Laravel 10 to 13. | Use when one shape is shared by input, output and generated TypeScript types. Not as a blanket replacement for form requests and API resources: pick one style per app. | 2026-11-27 |
| `laravel/horizon` | use | First-party dashboard and code-driven worker configuration for Redis queues. 5.x supports Laravel 12 and 13. | Only with a Redis queue connection; it does not manage database or SQS queues. Authorize the dashboard through its gate outside local. | 2026-11-27 |
| `laravel/telescope` | use | First-party inspector for requests, queries, jobs, mail and exceptions. 5.x supports Laravel 12 and 13. | Local development: require it with `--dev` and keep it out of package discovery, as its docs describe. In production only behind its gate, with filtering and scheduled pruning: it stores request data, including personal data. | 2026-11-27 |
| `laravel/pulse` | use | First-party production dashboard for slow queries, jobs, requests, cache use and busy users. 1.x supports Laravel 12 and 13. | Production metrics. It requires Livewire. Its tables grow with traffic: set sampling, and on busy apps give it its own database connection or the Redis ingest driver. | 2026-11-27 |
| `fruitcake/laravel-debugbar` | use | Debug toolbar with the queries, views, timings and memory of each request. The current name of the Laravel Debugbar package; 4.x supports Laravel 11 to 13. | Require it with `--dev`. Never enabled in production: it shows queries and request data. It follows `APP_DEBUG` unless `DEBUGBAR_ENABLED` is set. | 2026-11-27 |
| `barryvdh/laravel-debugbar` | avoid | Former name of `fruitcake/laravel-debugbar`. The project's README asks users to switch to the new name. | Replace it with `fruitcake/laravel-debugbar` in `require-dev`, following the README's upgrade note. | 2026-11-27 |
| `laravel/scout` | use | First-party full-text search on Eloquent models, with Algolia, Meilisearch, Typesense and database drivers. 11.x supports Laravel 12 and 13. | A real search feature. The database driver suits small tables; larger data sets need a search engine. Queue index updates. | 2026-11-27 |
| `spatie/laravel-medialibrary` | use | Attaches files to Eloquent models, with image conversions, responsive images and any filesystem disk. 11.x supports Laravel 12 and 13. | Files that belong to models. Needs the exif and fileinfo extensions and an image driver; queue the conversions. For one upload column, a path attribute and the filesystem are enough. | 2026-11-27 |
| `spatie/laravel-backup` | use | Backs up the database and chosen files to any filesystem disk, with cleanup and health monitoring. 10.x supports Laravel 12.40 and 13. | 10.x needs PHP 8.4 and the zip extension. Store backups off the server, schedule the monitor, and test a restore. A host's managed database backups may already cover the database. | 2026-11-27 |
| `spatie/laravel-activitylog` | use | Records user and model activity in a database table through a small API. 5.x supports Laravel 12 and 13. | 5.x needs PHP 8.4. Log only the attributes you need, and give rows that hold personal data a retention window (see `laravel-pitfalls`, PII in logs). One audit package per app. | 2026-11-27 |
| `owen-it/laravel-auditing` | depends | Records old and new attribute values for every model change, with user, IP address and URL resolvers. 14.x supports Laravel 11 to 13. | When a full change history per model is a requirement. Exclude attributes that hold secrets or personal data, and set a retention window. Not alongside another audit package. | 2026-11-27 |
| `sentry/sentry-laravel` | depends | Error and performance monitoring SDK for hosted or self-hosted Sentry. 4.x supports Laravel 6 to 13. | Only when the project's monitoring choice is Sentry (`laravel.monitoring` in the profile). Keep `send_default_pii` off unless the privacy policy covers it. | 2026-11-27 |
| `maatwebsite/excel` | depends | Excel and CSV imports and exports on top of PhpSpreadsheet, with chunked and queued jobs. 4.x supports Laravel 12 and 13. | Spreadsheets with formatting, formulas or several sheets. PhpSpreadsheet holds the workbook in memory, so for large plain exports a streaming writer such as `openspout/openspout` uses far less. | 2026-11-27 |
| `openspout/openspout` | use | Streaming CSV, XLSX and ODS reader and writer that keeps memory use low on very large files. Framework-agnostic. | Large plain imports and exports. 5.x needs PHP 8.4 or later. No formulas or charts; chunking and queueing are yours to write. | 2026-11-27 |
