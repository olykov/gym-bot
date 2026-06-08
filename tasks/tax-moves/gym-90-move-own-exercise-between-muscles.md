---
schema_version: 1
id: GYM-90
title: "Move OWN exercise between muscles (long-tap → Move to muscle; own-only; dedup vs target) — startable now"
slug: gym-90-move-own-exercise-between-muscles
status: in_progress
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T10:00:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-moves
depends_on: []
blocks: []
related: [GYM-89]
commits: [4e9b50d]
tests: []
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
