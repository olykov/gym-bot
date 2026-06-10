---
schema_version: 1
id: GYM-110
title: "Apply catalog curation: renames + demotes + merges (repoint training) via migration"
slug: gym-110-apply-catalog-curation
status: blocked
priority: high
type: feature
labels: [catalog, db, migration]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T02:00:00Z
start_date: null
finish_date: null
updated: 2026-06-10T02:00:00Z
epic: catalog-curation
depends_on: [GYM-111]
blocks: [GYM-92]
related: []
commits: []
tests: []
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
