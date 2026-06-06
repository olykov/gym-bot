---
schema_version: 1
id: GYM-80
title: "Contract: PATCH rename muscle/exercise + is_mine on read schemas + regen"
slug: gym-80-rename-contract
status: in_progress
priority: high
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T08:10:00Z
finish_date: null
updated: 2026-06-06T08:10:00Z
epic: phase-5
depends_on: []
blocks: [GYM-81, GYM-82]
related: [GYM-75]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-80 — Contract: rename + is_mine

## Problem
Operator wants a long-press "manage element" sheet (rename/delete) on muscle/exercise tiles. Delete/hide
endpoints already exist; rename (PATCH) does not. The client also needs to know which items are the user's
OWN custom ones (rename/delete allowed) vs global catalog (hide only) — `is_global`/`created_by` are
already exposed but a derived `is_mine` makes the gating unambiguous.

## Plan (api-contract-guardian)
1. Add `PATCH /muscles/{muscle_id}` and `PATCH /exercises/{exercise_id}` to `openapi.yaml`:
   - Request body: a `name` field with the SAME create-name constraints as `MuscleCreate.name` (30) /
     `ExerciseCreate.name` (40) — reuse the existing name pattern/limits (a `MuscleRename`/`ExerciseRename`
     schema, or reuse MuscleCreate/an inline name). 200 → `Muscle` / `Exercise`. Document: own custom items
     only (global → 403); duplicate name → 409. `get_principal` auth, tags `muscles`/`exercises`, 401/403/404/409.
2. Add `is_mine: boolean` to the `Muscle` and `Exercise` READ schemas (server-computed = the item is the
   caller's own custom record, i.e. created_by == caller and not global). Keep `is_global`/`created_by`.
3. `make validate` + regen both clients (`make gen-python`, `make gen-typescript`); confirm compile.

## Acceptance criteria
- [ ] PATCH rename for muscle + exercise in the spec (name-validated, own-only, 409 on dup); `is_mine` on
      Muscle + Exercise read schemas; both clients regenerated + compile; validate OK.

## Comments

### 2026-06-06T08:10:00Z — task created
Foundation for GYM-81 (API rename + delete-guard) and GYM-82 (long-press manage sheet).
