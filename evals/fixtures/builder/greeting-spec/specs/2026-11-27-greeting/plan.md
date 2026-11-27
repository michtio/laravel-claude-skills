---
id: PLAN-2026-11-27-greeting
prd: SPEC-2026-11-27-greeting
status: approved
approved_by: Acme
approved_on: 2026-11-27
---

# Plan: Greeting service

## Slices

### S1: GreetingService

- **Deliverable:** `app/Services/GreetingService.php`, a plain class with `greet(string $name): string`.
- **Requirements:** R1
- **Layers:** `app/Services/GreetingService.php`.
- **Verification gate:** `vendor/bin/pest` is green (no DDEV project in this fixture, so no other gate runs).
- **Gate tests:** from AC1 and AC2, by a separate gate writer, committed as `test(gate): S1`. The builder does not edit them.
- **Size:** S
