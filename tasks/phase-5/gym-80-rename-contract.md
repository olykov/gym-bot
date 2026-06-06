---
schema_version: 1
id: GYM-80
title: "Contract: PATCH rename muscle/exercise + is_mine on read schemas + regen"
slug: gym-80-rename-contract
status: done
priority: high
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T08:10:00Z
finish_date: 2026-06-06T16:10:00Z
updated: 2026-06-06T16:10:00Z
epic: phase-5
depends_on: []
blocks: [GYM-81, GYM-82]
related: [GYM-75]
commits: [caeb76c]
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

### 2026-06-06T16:10:00Z — contract implemented (commit caeb76c)
Edited `packages/api-contract/openapi.yaml` only.

Paths added (mirror existing DELETE-by-id style, `userJwt`/`serviceAuth` security, ActAsUser param):
- `PATCH /muscles/{muscle_id}` — operationId `renameMuscle`, tag `muscles`, body `MuscleRename`,
  200 → `Muscle`; responses 401/403/404/409/422.
- `PATCH /exercises/{exercise_id}` — operationId `renameExercise`, tag `exercises`, body
  `ExerciseRename`, 200 → `Exercise`; responses 401/403/404/409/422.

Rename body schemas: chose dedicated `MuscleRename` / `ExerciseRename` (each `{name}` only) rather
than reusing `*Create` — the create schemas carry extra fields (`ExerciseCreate.muscle_name`) that
rename must not accept, so a focused schema keeps the contract honest. Name constraints copied 1:1
from the GYM-75 create fields: muscle `minLength:1, maxLength:30`; exercise `minLength:1,
maxLength:40`; both share the GYM-75 pattern `^[A-Za-z0-9À-ÖØ-öø-ÿА-яЁё \-'.,()/&+°]+$`.

`is_mine: boolean` added to BOTH `Muscle` and `Exercise` read schemas (optional, matching the
sibling `is_global`/`created_by` which are also non-required), description: "true when this is the
caller's own custom record (rename/delete allowed); false for global catalog items (hide only)".

Reusable response components added (none existed before): `Forbidden` (403), `Conflict` (409),
`UnprocessableEntity` (422), all → `Error` schema.

Client impact: additive for read schemas (`is_mine` optional) and two new endpoints — non-breaking
for existing TS/admin and Python/bot consumers. New rename calls are opt-in per client.

Quality gate: `make validate` OK (33 paths, 37 schemas). Regenerated both clients —
`make gen-python` (committed `clients/python/.../models.py`: `MuscleRename`, `ExerciseRename`,
`is_mine` present; instantiation + empty-name rejection verified) and `make gen-typescript`
(`clients/typescript/schema.ts` is gitignored by design; `tsc --noEmit --strict` passes; contains
`renameMuscle`/`renameExercise` ops, `MuscleRename`/`ExerciseRename`, `is_mine`).
