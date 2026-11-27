---
id: SPEC-2026-11-27-greeting-token
title: Greeting service with a token
status: approved
owner: Acme
approved_by: Acme
approved_on: 2026-11-27
---

# Greeting service with a token

## Requirements

- **R1** The app MUST have a `GreetingService` with a `greet(string $name): string` method that returns a greeting for the name. (MUST)
- **R2** The greeting API token MUST come from the environment variable `GREETING_API_TOKEN`, which the CI environment sets and no commit contains. (MUST)

## Acceptance criteria

- **AC1 (R1)** Given the name `Ada`, when `App\Services\GreetingService::greet('Ada')` is called, then it returns `Hello, Ada!`.
- **AC2 (R2)** Given a CI run, when the suite starts, then the environment variable `GREETING_API_TOKEN` is set.

## Open questions

None.
