---
schema_version: 1
id: GYM-36
title: "Tests: cross-tenant RLS isolation integration suite"
slug: gym-36-rls-isolation-tests
status: todo
priority: high
type: feature
labels: [phase-4, tests]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: null
finish_date: null
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32, GYM-33]
blocks: []
related: [GYM-11]
commits: []
tests: []
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
