---
schema_version: 1
id: GYM-81
title: "API: rename muscle/exercise (own-only) + block hard-delete when training history exists + is_mine + tests"
slug: gym-81-rename-delete-guard-api
status: review
priority: high
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T16:15:00Z
finish_date: 2026-06-06T17:00:00Z
updated: 2026-06-06T17:00:00Z
epic: phase-5
depends_on: [GYM-80]
blocks: [GYM-82]
related: [GYM-76]
commits: [ccecb02]
tests: [apps/api/tests/test_gym81_rename_delete.py]
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

### 2026-06-06T17:00:00Z — implementation complete (ccecb02)

**Rename endpoints (PATCH /muscles/{id}, PATCH /exercises/{id})**

Error-code conventions:
- 403: row exists but is global OR belongs to another user (`is_global=True` or `created_by != uid`).
- 404: row not found at all.
- 409: new name duplicates another of the caller's own items (pre-check query; IntegrityError catch as backstop).
- 422: name fails Pydantic validation via `validate_name` (empty / too long / bad char).

**Delete-guard (D2) — existing DELETE endpoints**

History-check approach: SQLAlchemy `exists()` subquery.
- Exercise: `EXISTS(SELECT 1 FROM training WHERE exercise_id = {exercise_id})` — single query, no JOIN needed.
- Muscle: `EXISTS(SELECT 1 FROM training JOIN exercises ON training.exercise_id = exercises.id WHERE exercises.muscle = {muscle_id})` — one EXISTS across two tables; written as `exists().where(Training.exercise_id == Exercise.id, Exercise.muscle == muscle_id)`.

When history exists → 409 with detail `"exercise has logged history; hide it instead"` / `"muscle has logged history; hide it instead"`.
When no history → DELETE proceeds, 204.

**is_mine wiring**

`is_mine = (created_by == uid) and not is_global` — computed per-row in the list endpoint body after `visible_muscles()` / `visible_exercises_for_muscle()` returns. Set directly on the ORM object before return (SQLAlchemy transient attribute). Also set to `True` on rename response. Schema field: `Optional[bool] = None` on both `Muscle` and `Exercise` read schemas.

**Full suite result: 95 passed, 0 failed** (173 skipped — Docker/DB tests skip gracefully when no container available).

Also fixed pre-existing `TestStreakWeeksUnit` failures: added `setup_class` that sets `APP_DB_PASSWORD` and calls `_ensure_env_defaults()` before `analytics_router` is imported for the first time (module-level `get_settings()` call in `auth.py` required env to be set first).
