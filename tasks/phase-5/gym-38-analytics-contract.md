---
schema_version: 1
id: GYM-38
title: "Contract: 3 analytics endpoints in OpenAPI + regen clients"
slug: gym-38-analytics-contract
status: done
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T10:00:00Z
finish_date: 2026-06-04T11:00:00Z
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-39, GYM-41, GYM-42]
related: [GYM-12]
commits: [0056663]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-38 — Contract: analytics endpoints + regen clients

## Problem
The Mini App MVP needs activity-grid, summary, and exercise-progress data that the contract does not
yet define.

## Plan
Add to `packages/api-contract/openapi.yaml`, under the bot/user-facing (get_principal) auth:
- `GET /analytics/activity?from&to` → `[{ date, sets_count }]`
- `GET /analytics/summary` → `{ exercises, sets, prs, current_streak }`
- `GET /analytics/exercise-progress?muscle&exercise` → series shaped for ECharts (per-set weight/reps over time)
Regenerate BOTH clients (python + typescript). Keep naive-datetime tolerance (GYM-30).

## Acceptance criteria
- [ ] 3 endpoints in the spec; both clients regenerated and compile.

## Comments

### 2026-06-04T09:00:00Z — task created
Schemas must be exact — frontend (GYM-41/42) and API (GYM-39) both build on them.

### 2026-06-04T11:00:00Z — implemented (commit 0056663), status review
Added 3 read endpoints under the `get_principal` auth (userJwt OR serviceAuth + ActAsUser),
tag `analytics`, sibling-style 401 (Unauthorized) responses. No new 4xx beyond what siblings use.

Endpoints:
- `GET /analytics/activity?from=<date>&to=<date>` (both required) → `ActivityDay[]`
- `GET /analytics/summary` (no query) → `AnalyticsSummary`
- `GET /analytics/exercise-progress?muscle=<string>&exercise=<string>` (both required) → `ExerciseProgress`

Schemas (snake_case, naive-tolerant `date` per GYM-30 — no AwareDatetime):
- `ActivityDay { date: date, sets_count: integer }`
- `AnalyticsSummary { exercises: integer, sets: integer, prs: integer, current_streak: integer }`
- `ExercisePoint { date: date, weight: number, reps: number }`
- `ExerciseSetSeries { set: integer, points: ExercisePoint[] }`
- `ExerciseProgress { series: ExerciseSetSeries[] }`

Regenerated + verified:
- `make validate` → OK (28 paths, 27 schemas).
- `make gen` → python (datamodel-codegen, pydantic v2, `--output-datetime-class datetime`:
  `date` fields map to `datetime.date` via `date_aliased`) + typescript (`openapi-typescript@7`).
- Python: imported `gym_api_client.models`, instantiated all 5 models; `date` fields are `datetime.date`.
- TypeScript: `tsc --noEmit --strict --skipLibCheck clients/typescript/schema.ts` → exit 0;
  new types/paths present in `clients/typescript/schema.ts` (gitignored, regenerate with `make gen-typescript`).

Affected clients: TS (web/admin/miniapp) and python (bot) — additive only, no breaking changes.
GYM-39 (impl), GYM-41/42 (frontend) build on these exact shapes.
