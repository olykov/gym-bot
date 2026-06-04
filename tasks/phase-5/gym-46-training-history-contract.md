---
schema_version: 1
id: GYM-46
title: "Contract: training day-list, day-detail, DELETE set + regen clients"
slug: gym-46-training-history-contract
status: review
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-04T18:05:00Z
finish_date: 2026-06-04T19:10:00Z
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-47, GYM-48, GYM-49]
related: [GYM-12]
commits: [bf4d5ce86249f5c8cf280999e46f387ef38e8b48]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-46 — Contract: training history + edit

## Problem
The History (view + edit trainings) feature needs day-grouped reads and a delete; the contract only
has flat `GET /training`, `POST /training`, `PUT /training/{id}`.

## Plan
Add under the bot/user `get_principal` auth, tag `training`:
- `GET /training/days?from&to` → `TrainingDay[]` = `{ date: date, muscles: string[], exercises_count: int, sets_count: int }` (reverse-chrono; both query params optional → default window).
- `GET /training/day/{date}` → `TrainingDayDetail` = `{ date: date, exercises: TrainingDayExercise[] }` where `TrainingDayExercise = { exercise_id: int, exercise_name: string, muscle_name: string, sets: TrainingSet[] }` and `TrainingSet = { training_id: string, set: int, weight: number, reps: number }` (names denormalized so the client doesn't join).
- `DELETE /training/{training_id}` → 204 (RLS-scoped; only own).
`PUT /training/{id}` (TrainingUpdate weight/reps) already exists — unchanged. Naive-tolerant dates
(GYM-30). Regenerate python + typescript clients.

## Acceptance criteria
- [ ] 3 ops in the spec; both clients regenerated and compile.

## Comments

### 2026-06-04T18:00:00Z — task created
Shapes are exact — API (GYM-47) and frontend (GYM-49) build on them.

### 2026-06-04T19:10:00Z — contract added + clients regenerated
Added under `get_principal` auth (`userJwt` + `serviceAuth` + `ActAsUser` header), tag `training`,
sibling 401 (and 404 where the existing PUT/DELETE-style training/muscle/exercise endpoints declare it).
Existing `GET /training`, `POST /training`, `PUT /training/{training_id}` (TrainingUpdate) unchanged.
Fields snake_case; dates `format: date` (naive-tolerant, GYM-30).

Operations:
- `GET /training/days` — query `from` (date, optional), `to` (date, optional) → `TrainingDay[]`; 401.
  Day-grouped, reverse-chronological; omitting `from`/`to` returns a default window.
- `GET /training/day/{date}` — path `date` (date) → `TrainingDayDetail`; 401, 404.
- `DELETE /training/{training_id}` — path `training_id` (string) → `204 No Content`; 401, 404.
  Added as a sibling `delete` on the existing `/training/{training_id}` path (PUT unchanged).

Schemas (snake_case):
- `TrainingDay = { date: date, muscles: string[], exercises_count: integer, sets_count: integer }`
- `TrainingDayDetail = { date: date, exercises: TrainingDayExercise[] }`
- `TrainingDayExercise = { exercise_id: integer, exercise_name: string, muscle_name: string, sets: TrainingSet[] }`
- `TrainingSet = { training_id: string, set: integer, weight: number, reps: number }`

Regen + verify:
- `make validate` → OK: valid OpenAPI 3.1 (30 paths, 31 schemas).
- `make gen` → python (datamodel-code-generator, pydantic v2, `--output-datetime-class datetime`)
  + typescript (`openapi-typescript@7.13.0`) regenerated.
- Python: full package import OK; `TrainingDay`/`TrainingSet`/`TrainingDayExercise`/`TrainingDayDetail`
  instantiate; `date` parses to `datetime.date` (generated as aliased `date_aliased`, matching existing
  `ActivityDay`/`ExercisePoint`).
- TypeScript: `tsc --noEmit --strict` on `clients/typescript/schema.ts` → exit 0.
- New paths/operations/schemas present in both clients (TS `clients/typescript/schema.ts` is gitignored
  and regenerated on demand; only `openapi.yaml` + python `models.py` are tracked/committed).

Breaking-change check: all additive (new paths, new schemas, new sibling `delete`). No client migration
required for existing consumers; affected clients (when they adopt History): bot, admin/miniapp frontend.
