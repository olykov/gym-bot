---
schema_version: 1
id: GYM-84
title: "DB: normalized name_key + UNIQUE(name_key, scope) on muscles & exercises + backfill"
slug: gym-84-name-key-dedup
status: in_progress
priority: high
type: feature
labels: [taxonomy, db, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T12:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-foundation
depends_on: []
blocks: [GYM-85, GYM-86, GYM-87]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-84 — Normalized name_key + uniqueness

## Problem
"Bench Press", "bench-press", "bench_press", "BENCH  PRESS" must be treated as one name. Today nothing
enforces this, so lexical duplicates can accrue. See ADR 0001 (docs/adr/0001-exercise-taxonomy.md).

## Scope (layers)
- DB (Alembic migration, packages/db): add a `name_key` column to `muscles` and `exercises`, computed as
  casefold (NOT lower — Turkish/Cyrillic safe) + trim + collapse whitespace + unify hyphen/underscore/space
  + strip incidental punctuation. UNIQUE index on the appropriate scope: `(name_key, created_by)` for user
  rows and `(name_key)` for global/canonical (mirroring the existing partial unique indexes).
- Backfill `name_key` for all existing rows; resolve any existing collisions before adding the constraint.
- Document the exact normalization in docs/validation.md (extend the Name rules).

## Key decisions (operator)
- name_key is the dedup key; display name stays as typed.
- Normalization must be identical wherever it runs (DB backfill + API write path, GYM-85).

## Acceptance
- [ ] name_key present + UNIQUE on muscles & exercises; existing rows backfilled; collisions resolved;
      migration applies cleanly; normalization documented.
