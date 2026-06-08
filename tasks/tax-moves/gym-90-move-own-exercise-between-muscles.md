---
schema_version: 1
id: GYM-90
title: "Move OWN exercise between muscles (long-tap → Move to muscle; own-only; dedup vs target) — startable now"
slug: gym-90-move-own-exercise-between-muscles
status: review
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T10:00:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-moves
depends_on: []
blocks: []
related: [GYM-89]
commits: [4e9b50d, 6e44c16]
tests: [apps/api/tests/test_gym90_move_exercise.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-90 — Move own exercise between muscles

## Problem
A user may misplace an exercise (e.g. Squat under Chest). They need to move it to the right muscle —
independent of the taxonomy work and can ship NOW (operator: "можно вот сейчас уже сделать").

## Scope (layers): contract + API + frontend
- API: move an OWN exercise to another muscle (set its muscle); own-only; dedup against the target muscle
  by name_key (GYM-84). 403 on canonical/global (those are GYM-91's policy).
- Frontend (design plugin): long-tap on an exercise → manage sheet gains "Move to another muscle" → pick
  target muscle from the list → moved. Keep the existing manage-sheet design language.

## Acceptance
- [ ] Move an own exercise to another muscle from the manage sheet; own-only; dedup vs target; tests +
      build green.

## Comments

### 2026-06-08 — Contract slice (4e9b50d)
Added a dedicated move operation to `packages/api-contract/openapi.yaml`, mirroring the rename PATCH
(tag `exercises`, `get_principal` security: userJwt + serviceAuth + ActAsUser).

- Operation: `PATCH /exercises/{exercise_id}/muscle`, `operationId: moveExercise`.
- Request body: `ExerciseMove { muscle_id: integer (required) }` — target muscle id.
- Responses:
  - 200 → updated `Exercise`.
  - 401 → Unauthorized.
  - 403 → Forbidden (exercise is global/canonical or not the caller's own; canonical placement is
    GYM-91's decision, rejected here).
  - 404 → NotFound (exercise or target muscle not found / not visible to caller).
  - 409 → Conflict (caller already has an exercise with the same name under the target muscle —
    unique `(name, muscle, created_by)` collision).
- Used a dedicated `.../muscle` sub-resource rather than overloading the rename PATCH, leaving the
  working rename contract untouched.

Regenerated both clients: `make validate` OK (34 paths, 38 schemas); `make gen-python` +
`make gen-typescript` clean. TS client `tsc --noEmit --strict` exit 0; Python client imports
(`ExerciseMove(muscle_id=7)` round-trips). `moveExercise` + `ExerciseMove` present in both generated
outputs. The TS `schema.ts` is gitignored (regenerated on demand), so only `openapi.yaml` and the
Python `models.py` are committed.

Affected clients: Python (bot) and TypeScript (web/admin/miniapp) — purely additive, no breaking
change to existing operations.

### 2026-06-08 — API slice (6e44c16)

Implemented `PATCH /exercises/{exercise_id}/muscle` in `apps/api/`.

**Endpoint behavior:**
- Resolves the exercise first (single query, no filter on ownership) to distinguish 404 (not found)
  from 403 (found but global/unowned). Global exercises → 403; exercises invisible under RLS (e.g.
  another user's private exercise) → 404 (RLS fail-closed, row simply not returned).
- Target muscle visibility: uses `visible_muscles(db, uid)` from `app.services.visibility` — returns
  global muscles plus the caller's own private muscles, with the soft-hide layer applied. Muscle not
  in that set → 404.
- On success: sets `exercise.muscle = target_muscle_id`, commits, refreshes, sets `is_mine=True`.

**Error-code conventions:**
- 404: exercise not found (or hidden by RLS); target muscle not found or not visible to caller.
- 403: exercise exists and is visible but is global/canonical (or, in theory, unowned — in practice
  RLS returns 404 for truly unowned rows).
- 409: caller already has an exercise with the same name under the target muscle (unique index
  `(name, muscle, created_by)`). Pre-checked via a query; `IntegrityError` caught as backstop with
  rollback so the session stays usable.

**Collision handling:**
- Pre-check query before the UPDATE: if `(name, target_muscle, uid)` already exists → 409.
- `IntegrityError` catch after commit as backstop → rollback + 409.
- 409 detail: `"You already have an exercise named '...' under that muscle"`.

**Schema addition:** `ExerciseMove { muscle_id: int }` added to `app/schemas/schemas.py` after
`ExerciseRename` (same pattern, no validators needed — muscle_id is an integer FK).

**Full-suite pytest result:** 278 passed, 0 failed, 13 warnings.
