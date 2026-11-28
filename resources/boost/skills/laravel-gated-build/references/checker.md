# Checker sizing

Size an outside builder's commits with `git diff --numstat <base>..HEAD` and choose the `laravel-review-checker` lens from the line count and whether the diff touches a sensitive path.

Sensitive paths: request input reaching a write or a query, policies, gates and middleware, raw SQL, unescaped Blade, `$guarded` or `$fillable` changes, webhooks, auth flows, migrations on existing tables, `config/` and env keys.
