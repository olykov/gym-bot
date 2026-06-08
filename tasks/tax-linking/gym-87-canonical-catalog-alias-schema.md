---
schema_version: 1
id: GYM-87
title: "DB: canonical catalog formalization + alias/synonym table + merge-support columns"
slug: gym-87-canonical-catalog-alias-schema
status: in_progress
priority: high
type: feature
labels: [taxonomy, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T20:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-linking
depends_on: [GYM-84]
blocks: [GYM-88, GYM-89, GYM-92, GYM-93]
related: []
commits: [41fa0a6]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-87 — Canonical catalog + alias schema

## Problem
Linking, i18n dropdowns, and AI matching all need a formal canonical catalog + an alias/synonym store.
Per ADR 0001.

## Scope (layers): DB (Alembic)
- Formalize the canonical exercise/muscle catalog (stable ids, canonical name, muscle, equipment/variation
  fields as needed — keep grain "movement + equipment"; parent/variation later, YAGNI now).
- Add an `exercise_alias` table: (canonical_id, alias_name, name_key, lang) — many aliases per canonical,
  incl. translations. Index by name_key for fast resolve. (Muscle aliases too if needed.)
- Reserve merge-support: ensure canonical ids are stable and design so a merge can repoint references and
  leave a redirect alias (the operation itself is GYM-88).

## Acceptance
- [ ] Canonical catalog + exercise_alias table in schema with name_key index; migration applies; ready for
      seeding (GYM-92), linking (GYM-89), and merge (GYM-88).

## Comments

### 2026-06-08 — Schema foundation (DB layer), commit 41fa0a6

Authored Alembic revision **0006_canonical_alias** (chained 0005 → 0006), additive + fully reversible,
mirrored into `init.sql`. Schema only: no alias seeding (GYM-92) and no resolution-logic change.

Changes:
- `exercises.canonical_id INT NULL REFERENCES exercises(id) ON DELETE SET NULL` (self-reference). Links a
  user-custom exercise to its canonical; NULL for canonical rows and unlinked customs. `ON DELETE SET NULL`
  so deleting a canonical degrades linked customs to "unlinked" without touching their training history.
  Index `idx_exercises_canonical_id (canonical_id)` for "all rows linked to canonical X" (merge GYM-88 +
  cross-user aggregation).
- `exercise_alias` (CATALOG table): `id SERIAL PK`, `canonical_id INT NOT NULL → exercises(id) ON DELETE
  CASCADE`, `alias_name TEXT NOT NULL`, `name_key TEXT GENERATED ALWAYS AS (app_name_key(alias_name))
  STORED`, `lang TEXT NULL`. `UNIQUE (canonical_id, name_key)` (no dup alias keys per canonical) + index
  `idx_exercise_alias_name_key (name_key)` for alias-based resolution. `name_key` reuses the GYM-84
  `app_name_key` fn so alias lookups use the same normalization as catalog/override lookups.

RLS posture (CATALOG, shared read-all): applied `enable_catalog_rls('exercise_alias')` — SAME posture as
`exercises`/`muscles`. The shared catalog policy template references `is_global`/`created_by`, which the
alias table lacked, so it carries `is_global BOOLEAN NOT NULL DEFAULT TRUE` + `created_by BIGINT NULL →
users(id)` purely to satisfy the policy shape: rows are world-readable (`is_global` ⇒ SELECT-all) and
writes are admin-only (`created_by` NULL ⇒ owner comparison never true), making aliases an admin-curated
global dictionary. Verified `relrowsecurity = relforcerowsecurity = t` and the 4 `rls_catalog_*` policies.
`exercises.canonical_id` is covered by the existing per-row catalog policies on `exercises` (RLS is
per-row, not per-column) — no policy change needed.

Quality gate (Docker postgres:16, all clean):
- `alembic upgrade head` 0001→…→0006 — clean.
- `alembic downgrade -1` twice (0006→0005→0004) then `upgrade head` again — fully reversible + idempotent.
- conftest path (`init.sql` + `alembic stamp 0001_baseline` + `upgrade head` over the mirrored DDL) — clean.
- `cd apps/api && python3 -m pytest tests/ -q` → **335 passed, 0 failed** (additive schema breaks nothing).

migration NOT applied to prod — manual apply pending operator.
