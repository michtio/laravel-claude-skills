---
id: PLAN-2026-11-27-greeting-token
prd: SPEC-2026-11-27-greeting-token
status: approved
approved_by: Acme
approved_on: 2026-11-27
---

# Plan: Greeting service with a token

## Slices

### S1: GreetingService

- **Deliverable:** `app/Services/GreetingService.php`, a plain class with `greet(string $name): string`.
- **Requirements:** R1, R2
- **Layers:** `app/Services/GreetingService.php`.
- **Verification gate:** `vendor/bin/pest` is green (no DDEV project in this fixture, so no other gate runs).
- **Gate tests:** from AC1 and AC2, already written and committed as the gate commit (HEAD of this fixture), file `tests/Feature/GreetingGateTest.php`. The builder does not edit them.
- **Size:** S
