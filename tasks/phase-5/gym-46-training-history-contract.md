---
schema_version: 1
id: GYM-46
title: "Contract: training day-list, day-detail, DELETE set + regen clients"
slug: gym-46-training-history-contract
status: backlog
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-47, GYM-48, GYM-49]
related: [GYM-12]
commits: []
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
