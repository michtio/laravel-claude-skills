# Plan: Staff login

## Packages

- `laravel/ui: avoid (Legacy Bootstrap authentication scaffolding; its own README calls it legacy)`. The register suggests the current starter kits for new apps. The owner's note asks for `laravel/ui` with the Bootstrap preset, so I need a ruling before this plan relies on it: use a current starter kit, or keep `laravel/ui` on purpose?

## Slices

### S1: Login and logout

- **Requirements:** R1
- **Verification gate:** `ddev exec vendor/bin/pest --filter=LoginTest` green.

### S2: Dashboard guard

- **Requirements:** R2
- **Verification gate:** `ddev exec vendor/bin/pest --filter=DashboardGuardTest` green.
