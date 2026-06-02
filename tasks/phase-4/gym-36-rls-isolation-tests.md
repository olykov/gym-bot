---
schema_version: 1
id: GYM-36
title: "Tests: cross-tenant RLS isolation integration suite"
slug: gym-36-rls-isolation-tests
status: review
priority: high
type: feature
labels: [phase-4, tests]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: 2026-06-02T03:10:00Z
finish_date: 2026-06-02T00:00:00Z
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32, GYM-33]
blocks: []
related: [GYM-11]
commits: [380ecdd]
tests:
  - apps/api/tests/conftest.py
  - apps/api/tests/test_rls_isolation.py
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-36 — Tests: cross-tenant RLS isolation integration suite

## Problem
RLS must be proven, not assumed. First real test suite for the repo (pytest).

## Plan
- pytest integration tests against a backup-seeded local Postgres (real policies):
  - As user A (GUC set): sees only A's training/custom muscles/exercises/hidden/profile.
  - As user A: cannot SELECT/UPDATE/DELETE user B's rows (0 rows / 0 rowcount).
  - No GUC set: every table returns 0 rows (fail-closed).
  - role=admin: sees all rows across users.
  - Catalog: A sees global rows; cannot UPDATE/DELETE a global row; can modify own private.
- Record test paths in GYM-11 `tests[]`.

## Acceptance criteria
- [ ] Suite passes locally; cross-tenant assertions all green.

## Comments

### 2026-06-02T00:00:00Z — task created
Establishes the pytest harness the repo currently lacks.

### 2026-06-02T00:00:00Z — implementation complete (commit 380ecdd)
32 tests, 32 passed, 0 failed (pytest 9.0.3, Python 3.14.2, Postgres 16 via Docker).

Suite breakdown:
- TestUserAVisibility (7): user A sees own training/muscles/exercises/hidden/users/global rows.
- TestCrossTenantIsolation (8): user A gets 0 rows/rowcount on B's rows; INSERT as B raises.
- TestFailClosed (7): user-owned tables return 0 with no principal; private catalog rows hidden;
  global catalog rows remain visible (correct: is_global is intentionally world-readable).
- TestAdminVisibility (5): role='admin' sees all rows across both users.
- TestCatalogOwnership (5): A can create own private exercise; cannot UPDATE/DELETE global rows
  (0 rowcount); can UPDATE own private muscle; cannot UPDATE B's private muscle.

Full pytest output: 32 passed in 5.39s
