---
schema_version: 1
id: GYM-51
title: "History v2: add a set retroactively + move a set (date/exercise)"
slug: gym-51-history-v2-add-move
status: in_progress
priority: low
type: feature
labels: [phase-5, frontend, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-09T00:00:00Z
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: [fba7842]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-51 — History v2: add + move sets

## Problem
v1 (GYM-49) does view + edit weight/reps + delete. The operator wants, as the NEXT step, the ability
to add a set retroactively and move a set to another day/exercise.

## Plan (v2, after v1 ships)
- Add a set within a day/exercise (`POST /training` with an explicit date) — needs the create path to
  accept a date (today's create is `NOW()`); contract + API tweak.
- Move a set: change its `date` and/or `exercise_id` (a PUT extension or a dedicated endpoint) +
  cache invalidation. UX in the day-detail/editor.

## Acceptance criteria
- [ ] Add-set and move-set work end-to-end with isolation + cache invalidation.

## Comments

### 2026-06-04T18:00:00Z — task created
Deferred from the History plan (KISS); operator confirmed it's the planned next step after v1.

### 2026-06-09T00:00:00Z — contract slice (fba7842)
Contract-only slice of v2 landed in `packages/api-contract/`:

- RETROACTIVE ADD — added an OPTIONAL `date` (format `date`, naive-tolerant per GYM-30)
  field to `TrainingCreate`. When provided, the set is logged on that calendar day; when
  omitted the server uses now() (unchanged, backward-compatible). Additive, non-breaking.
- MOVE — added `PATCH /training/{training_id}/move` (operationId `moveTrainingSet`, tag
  `training`, userJwt/serviceAuth = get_principal). Existing PUT weight/reps edit untouched.
- `TrainingMove` request schema — all OPTIONAL: `date` (format `date`), `muscle_name` +
  `exercise_name` (lookup-name references, no length/char cap, mirroring `TrainingCreate`).
  At least one of {date, (muscle_name + exercise_name)} required (documented; full validation
  enforced in the API). Responses: 200 → `Training`; 401; 404 (set not found / not owned);
  409 (target day+exercise already has a set with the same set number — collision); 422
  (invalid body / nothing to move / target exercise not found).
- `make validate` passed (37 paths, 39 schemas). Regenerated both clients: Python models
  (`py_compile` OK — `date: date_aliased | None`, `TrainingMove` all-optional) and the
  TypeScript schema (`tsc --noEmit --strict` clean; `date?`, `TrainingMove`, `moveTrainingSet`
  present). TS schema is gitignored (regenerated on demand); Python models committed.

Affected clients: bot (Python), web/admin/miniapp (TypeScript) — additive `date` is safe to
adopt incrementally; `moveTrainingSet`/`TrainingMove` are new (no breaking change to existing
operations). API implementation of the new op + create-with-date is a separate (core-api) slice.
