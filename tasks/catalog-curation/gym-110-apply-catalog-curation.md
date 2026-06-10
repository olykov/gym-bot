---
schema_version: 1
id: GYM-110
title: "Apply catalog curation: renames + demotes + merges (repoint training) via migration"
slug: gym-110-apply-catalog-curation
status: done
priority: high
type: feature
labels: [catalog, db, migration]
assignee: null
model: claude-opus-4-8
reporter: oleksii
created: 2026-06-10T02:00:00Z
start_date: 2026-06-10T03:00:00Z
finish_date: 2026-06-10T03:00:00Z
updated: 2026-06-10T03:00:00Z
epic: catalog-curation
depends_on: [GYM-111]
blocks: [GYM-92]
related: []
commits: [55e3442]
tests: ["apps/api/tests/test_gym110_catalog_curation.py"]
design_reports: ["docs/adr/0004-canonical-catalog-governance.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-110 — Apply catalog curation (migration)

## Problem
Execute the operator-reviewed curation worksheet (`packages/db/seeds/canonical_curation.tsv`) against the
catalog per ADR 0004: ~97 KEEP (rename), ~19 DEMOTE (→ operator personal), 5 MERGE (repoint training + delete).

## Plan
A single tested data migration (chains after head; auto-applies on deploy via GYM-107):
- KEEP: `UPDATE exercises SET name=<canonical> WHERE id=<id>` (id stable → history intact).
- DEMOTE: `UPDATE exercises SET is_global=false, created_by=<olykov users.id> WHERE id=<id>`.
- MERGE A→B: `UPDATE training SET exercise_id=B WHERE exercise_id=A;` then `DELETE FROM exercises WHERE id=A`
  (also repoint user_hidden_exercises / user_exercise_override if present). Merge map in the worksheet.
- Bulgarian rename-swap: 373→"Bulgarian Split Squat" KEEP, 48→"Bulgarian Split Squat (Barbell)" DEMOTE, 40→373.
- Resolve `created_by` to the operator's `users.id` (telegram olykov / 2107709598) at migration time.
- Tested against a real DB: history counts preserved (sum of merged sets), no orphaned training rows,
  name_key uniqueness holds.

## Status
BLOCKED on: operator's FINAL polish of the worksheet + GYM-111 cross-map names.

## Comments

### 2026-06-10T02:00:00Z — created
Blocked pending the polished worksheet (operator) + GYM-111 (free-exercise-db names). Operator approved the
model: DEMOTE = is_global=false + created_by=olykov; Bulgarian rename-swap; merges as listed.

### 2026-06-10T03:00:00Z — done (migration 0008 applied + tested)
Migration `packages/db/alembic/versions/0008_apply_catalog_curation.py` (revises `0007_pg_trgm`),
GENERATED from `canonical_curation.tsv` v3.1 with values embedded (TSV not read at runtime).

Operation counts (per the worksheet, parsed + verified):
- **98 KEEP** renames (`UPDATE exercises SET name WHERE id`).
- **18 DEMOTE** (`SET name, is_global=false, created_by=2107709598 WHERE id`).
- **5 MERGE** (repoint `training` + defensively `user_hidden_exercises`/`user_exercise_override`,
  then `DELETE` source): 26->127, 347->54, 351->362, 338->30, 40->373.
- **1 junk delete**: id 337 (0 sets, not in worksheet).

Order is load-bearing: KEEP/DEMOTE renames first, then MERGEs, then the 337 delete — so merge
targets that are themselves renamed (e.g. 30 -> "Dumbbell Bench Press", 373 -> "Bulgarian Split
Squat") end correctly named before their sources fold in. All names are bound parameters, so the
34 names containing parentheses are escaped by the driver; no name in v3.1 contains an apostrophe.
`downgrade()` raises `NotImplementedError` (deliberate one-way curation; restore from backup to revert).

Worksheet internal-consistency checks passed: no duplicate ids; all 5 merge targets are valid
KEEP/DEMOTE rows and none is itself a merge source; 351 (Forearms) and 362 (Biceps) share a
name_key but live in different muscles, so the global `(name_key, muscle)` unique is not violated.

Green gate (real Postgres 16 via Docker, no skipped integration tests):
- Focused test `apps/api/tests/test_gym110_catalog_curation.py` seeds a representative pre-curation
  catalog (5 merge sources + targets, id 337, the operator 2107709598 + another user 343459661,
  training on merge sources/targets, a demote target, and 367 other-user data), runs
  `alembic upgrade head`, then asserts: training count unchanged (24), merge sums preserved on
  targets, zero orphan training rows, sources+337 gone, DEMOTE rows personal+renamed, KEEP rows
  renamed+global, both name_key partial unique indexes satisfied, and re-run idempotency.
- Full suite: **407 passed, 0 skipped, 0 failed** (DB up).

Branch `catalog/gym-110-apply`, commit 55e3442. NOT merged to main / not applied to prod.
