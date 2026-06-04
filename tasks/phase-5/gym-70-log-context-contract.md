---
schema_version: 1
id: GYM-70
title: "Contract: GET /analytics/log-context (completed-sets + last-session + PR in one) + regen"
slug: gym-70-log-context-contract
status: review
priority: high
type: feature
labels: [phase-5, api-contract, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T08:00:00Z
start_date: 2026-06-05T08:00:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-71, GYM-72]
related: [GYM-64, GYM-69]
commits: [150536a]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-70 — Contract: log-context

## Problem
The record Phase-B currently fires 3 reads per exercise (completed-sets, personal-record, + a needed
last-session lookup) → noticeable latency (roundtrips, not SQL). Combine into ONE endpoint, and change
pre-fill from PR to the **last recorded value of that set #** (operator feedback #3/#4).

## Plan
Add `GET /analytics/log-context?muscle&exercise&date` → `LogContext`:
- `completed_sets: integer[]` — set numbers already logged on `date` for this exercise (auto next set#).
- `last_session_sets: LogSet[]` — the most recent PRIOR session's sets, `LogSet = {set:int, weight:number, reps:number}` (pre-fill set N = last session's set N).
- `pr: PersonalRecord | null` — `{weight, reps, date}` (the PR chip "{w}kg × {r}").
Under `get_principal` auth, tag `analytics`, sibling 401. Naive-tolerant dates (GYM-30). Regen python +
typescript clients. (Existing completed-sets / personal-record stay for other callers.)

## Acceptance criteria
- [ ] log-context + LogContext/LogSet in the spec; both clients regenerated + compile.

## Comments

### 2026-06-05T08:00:00Z — task created
One roundtrip for the whole set-logger context; replaces the PR pre-fill with last-session per-set.

### 2026-06-05 — contract added + clients regenerated (150536a)
Added `GET /analytics/log-context?muscle&exercise&date` under `get_principal` auth (userJwt +
serviceAuth + ActAsUser), tag `analytics`, sibling 401. Reuses `MuscleNameQuery`/`ExerciseNameQuery`
params + a required `date` (format: date, naive-tolerant GYM-30) mirroring `/analytics/completed-sets`.

New schemas (additive only; existing completed-sets / personal-record endpoints UNCHANGED):
- `LogContext = { completed_sets: integer[], last_session_sets: LogSet[], pr: PersonalRecord | null }`
  — all three required (pr nullable via oneOf [PersonalRecord, null]); reuses existing `PersonalRecord`.
- `LogSet = { set: integer, weight: number, reps: number }`.

Regen/verify: `make validate` OK (33 paths, 35 schemas). `make gen-python` (datamodel-code-generator,
pydantic v2, --output-datetime-class datetime) + `make gen-typescript` (openapi-typescript@7) both
regenerated. Python client imports; `LogContext`/`LogSet` instantiate; `pr` accepts both `None` and a
`PersonalRecord`. TS `tsc --noEmit --strict` on the generated schema exits 0. New path + types present
in both clients.

Affected clients: python (gym-api-client) and typescript (web/admin/miniapp) — both regenerated.
Purely additive; no breaking change.
