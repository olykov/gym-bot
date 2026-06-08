---
schema_version: 1
id: GYM-86
title: "DB+API+frontend: per-user exercise override (canonical_id + display_name) — rename a canonical keeps the link"
slug: gym-86-canonical-reference-overrides
status: in_progress
priority: high
type: feature
labels: [taxonomy, db, api, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T20:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-foundation
depends_on: [GYM-84]
blocks: [GYM-89]
related: []
commits: [41fa0a6]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-86 — Reference + overrides

## Problem
A user should be able to rename a CANONICAL exercise to their own name while the canonical link persists
(so ratings/PRs still aggregate). Today rename only works on a user's OWN custom row. Per ADR 0001.

## Scope (layers): DB + API + frontend
- DB: introduce the per-user override seam — either a `user_exercise` row referencing `canonical_id` with
  a `display_name` override (+ hidden/sort), or equivalent columns. Same for muscles if we want canonical
  muscle aliases (decide; muscles are a small stable taxonomy). Migration + RLS (user-owned override rows).
- API: renaming a canonical creates/updates the caller's override (alias) rather than mutating the shared
  row; reads return the effective display_name but keep canonical_id; hide/move/etc. operate on the override.
- Frontend: rename of a canonical now allowed (produces an alias); the tile shows the user's name; manage
  sheet reflects the link. Shared surfaces must still use the canonical name (note for later).

## Key decisions (operator)
- Display = user's alias; identity = canonical_id (preserved).

## Acceptance
- [ ] Renaming a canonical exercise stores a per-user alias with canonical_id intact; personal views show
      the alias; canonical identity unchanged for everyone else; tests + build/suite green.

## Comments

### 2026-06-08 — Schema foundation (DB layer only), commit 41fa0a6

Authored Alembic revision **0005_user_overrides** (chained 0004 → 0005), additive + fully reversible,
mirrored into `init.sql`. API/frontend layers (effective-name reads, rename-creates-override) remain
TODO per the task scope.

Tables added (both user-owned, one override row per user per referenced entity):
- `user_exercise_override`: `user_id BIGINT NOT NULL → users(id)`,
  `exercise_id INT NOT NULL → exercises(id) ON DELETE CASCADE`, `display_name TEXT NOT NULL`,
  `display_name_key TEXT GENERATED ALWAYS AS (app_name_key(display_name)) STORED`.
  PK `(user_id, exercise_id)`; index `idx_user_exercise_override_name_key (user_id, display_name_key)`
  for name→id resolution.
- `user_muscle_override`: same shape against `muscle_id INT NOT NULL → muscles(id) ON DELETE CASCADE`.
  PK `(user_id, muscle_id)`; index `idx_user_muscle_override_name_key (user_id, display_name_key)`.

Type note: `user_id` is `BIGINT` (not `int`) to MATCH the existing FK/type used by
`user_hidden_exercises`/`user_hidden_muscles` (their `user_id` is `BIGINT REFERENCES users(id)`, since
`users.id` is BIGINT). `exercise_id`/`muscle_id` are `INT` matching the SERIAL catalog PKs.

RLS posture (user-owned, per-row, fail-closed): applied `enable_user_rls(table,'user_id')` on BOTH
tables — IDENTICAL posture to `user_hidden_muscles`/`user_hidden_exercises`. ENABLE + FORCE RLS + four
PERMISSIVE CRUD policies keyed on the `app.user_id` GUC under role `app_rw` (admin branch bypasses).
`app_rw` inherits CRUD/sequence grants via the `ALTER DEFAULT PRIVILEGES` set in 0002_rls — no extra
GRANT needed. Verified `relrowsecurity = relforcerowsecurity = t` and the 4 `rls_user_*` policies on
each table.

`display_name_key` is intentionally NOT unique: a user may rename two canonical rows to colliding keys;
the add/rename dedup decision lives in the API (GYM-89), not as a hard DB constraint here.

Quality gate (Docker postgres:16, all clean):
- `alembic upgrade head` 0001→…→0006 — clean.
- `alembic downgrade -1` twice (0006→0005→0004) then `upgrade head` again — fully reversible + idempotent.
- conftest path (`init.sql` + `alembic stamp 0001_baseline` + `upgrade head` over the mirrored DDL) — clean,
  no conflicts.
- `cd apps/api && python3 -m pytest tests/ -q` → **335 passed, 0 failed** (additive schema breaks nothing).

migration NOT applied to prod — manual apply pending operator.
