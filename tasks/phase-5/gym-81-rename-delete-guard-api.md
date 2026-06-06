---
schema_version: 1
id: GYM-81
title: "API: rename muscle/exercise (own-only) + block hard-delete when training history exists + is_mine + tests"
slug: gym-81-rename-delete-guard-api
status: in_progress
priority: high
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T16:15:00Z
finish_date: null
updated: 2026-06-06T08:10:00Z
epic: phase-5
depends_on: [GYM-80]
blocks: [GYM-82]
related: [GYM-76]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-81 — API: rename + delete-guard + is_mine

## Problem
Implement rename for muscle/exercise (own custom only) and make hard-delete safe: per operator decision
**D2**, block hard-delete of an item that has logged training history (offer hide instead) so history is
never silently destroyed. Also populate the `is_mine` read field (GYM-80).

## Plan (core-api-engineer)
- **Rename** — add `PATCH /muscles/{muscle_id}` + `PATCH /exercises/{exercise_id}` (apps/api):
  - Own custom only: `created_by == uid` and not global; else 403. 404 if not found.
  - Validate the new name via the existing `validate_name` (max 30 muscle / 40 exercise) — reuse GYM-76.
  - Duplicate name for this user (unique index `(name, created_by)`) → 409 (catch the integrity error or
    pre-check), clear message. Return the updated `Muscle`/`Exercise`.
- **Delete-guard (D2)** — on the EXISTING private-delete endpoints (`DELETE /muscles/{id}`,
  `DELETE /exercises/{id}`): before deleting, check for training history:
  - Exercise: block if any `training` row references it → 409 `{detail: "has logged history; hide instead"}`.
  - Muscle: block if any exercise under it has training history → 409 same shape. (A muscle/exercise with
    NO history still deletes cleanly.)
  - Global-item "delete" stays as the existing per-user HIDE endpoints (unchanged).
- **is_mine** — populate on the Muscle/Exercise read responses (= `created_by == uid and not is_global`).
  Apply wherever those schemas are serialized in the muscle/exercise LIST endpoints the Mini App uses.
- **Tests** (`apps/api/tests/test_gym81_rename_delete.py`): rename own muscle/exercise OK (name normalized,
  validated); rename global → 403; rename to a dup name → 409; rename invalid name → 422; delete own item
  WITH history → 409; delete own item WITHOUT history → 204; `is_mine` true for own / false for global.
  FULL `apps/api` suite green (0 failed).

## Acceptance criteria
- [ ] Rename own-only (403 global, 409 dup, 422 invalid); hard-delete blocked when history exists (409),
      allowed when empty (204); `is_mine` correct on read; tests green; full suite 0 failed.

## Comments

### 2026-06-06T08:10:00Z — task created
Depends on GYM-80 (contract). Reuses existing hide + private-delete endpoints; adds rename + delete-guard.
