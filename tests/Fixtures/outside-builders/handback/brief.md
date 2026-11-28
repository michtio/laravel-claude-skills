# Brief: S1 export status

Slice: S1
Project root: /work/orders-app
Laravel version: 13.0
Gate commit: 3f2a9c1
Gate files: tests/Feature/OrderExportTest.php
Pest command: ddev exec vendor/bin/pest tests/Feature/OrderExportTest.php

## R2

The export MUST include a status column.
AC2: Given an order with status shipped, when the CSV is exported, then the row has `shipped` in the status column.

### R3 notes

A level 3 heading is not a requirement id.

## R5: Reject unknown status

The export MUST reject an unknown status filter.
AC5: Given the filter `status=bogus`, when the export runs, then it responds 400.

## Pointers

- .claude/skills/laravel-pitfalls/SKILL.md
- CLAUDE.md

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
- Commit your work before writing the hand-back.
