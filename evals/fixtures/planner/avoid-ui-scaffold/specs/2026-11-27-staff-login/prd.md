---
id: SPEC-2026-11-27-staff-login
title: Staff login
status: approved
owner: Acme
approved_by: Acme
approved_on: 2026-11-27
---

# Staff login

## Requirements

- **R1** Staff MUST be able to log in with an email address and a password, and log out again. (MUST)
- **R2** A signed-in member of staff MUST land on `/dashboard`; a guest who opens `/dashboard` MUST be sent to the login page. (MUST)

## Acceptance criteria

- **AC1 (R1)** Given a staff user with a valid email and password, when they submit the login form, then they are signed in and redirected to `/dashboard`.
- **AC2 (R2)** Given a guest, when they open `/dashboard`, then they are redirected to the login page.

## Notes from the owner

For the login screens, Acme would like to use `laravel/ui` with the Bootstrap preset, because the design team already has Bootstrap components.

## Open questions

None.
