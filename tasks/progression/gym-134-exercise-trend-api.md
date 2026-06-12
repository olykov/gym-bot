---
schema_version: 1
id: GYM-134
title: "API + contract: GET /analytics/exercise-trend (session volume delta + e1RM trend series)"
slug: gym-134-exercise-trend-api
status: review
priority: medium
type: feature
labels: [api, contract, progression, analytics]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:35:00Z
start_date: 2026-06-12T18:10:00Z
finish_date: null
updated: 2026-06-12T18:10:00Z
epic: progression
depends_on: []
blocks: [GYM-135]
related: [GYM-71, GYM-133]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-134 — exercise-trend API

## Problem
Concept doc 03 §4.2. Phase-2 surfaces (SetLogger sparkline, session-vs-session volume
delta in the summary) need one small server read; computing multi-week trends client-side
would mean pulling full progress series into the record sheet.

## Solution
- Contract first (`packages/api-contract/openapi.yaml`):
  `GET /analytics/exercise-trend?muscle&exercise&weeks=8` →
  `{ last_session: {date, volume}, prev_session: {date, volume} | null,
     e1rm_trend: [{date, e1rm}] }` — per-session max-e1RM points over the window.
- apps/api `analytics_router`: RLS-scoped, name-resolved like log-context (GYM-71 pattern);
  sargable on `idx_training_user_exercise`; analytics cache + GYM-47 invalidation keys.
- Regenerate the TS client; no frontend consumption here (GYM-135).
- Tests: volume math, prior-session selection (mirrors GYM-71 prior-day CTE), e1RM points,
  isolation, empty history → nulls/[]; EXPLAIN shows index use.

## Acceptance criteria
- [ ] Endpoint live + cached + RLS-tested; contract + generated client updated; tests green.
      (code + contract + both generated clients done; integration tests WRITTEN but require
      live Postgres — operator must run the api suite, e.g. `make test`-equivalent for apps/api)

## Comments

### 2026-06-12T10:35:00Z — task created
Mirrors the GYM-70/71 contract→API split discipline in one task (small enough).

### 2026-06-12T18:10:00Z — implemented (agent wave 7b)
Files:
- `packages/api-contract/openapi.yaml` — `GET /analytics/exercise-trend?muscle&exercise&weeks`
  (weeks 1..52, default 8) + schemas `ExerciseTrend` / `SessionVolume` / `E1rmPoint`
  (`last_session`/`prev_session` nullable, `e1rm_trend` array — same oneOf-null style as LogContext.pr).
- `packages/api-contract/clients/python/gym_api_client/models.py` — regenerated (datamodel-codegen,
  exact Makefile flags); `clients/typescript/schema.ts` — regenerated (openapi-typescript@7).
- `apps/api/app/schemas/schemas.py` — `SessionVolume`, `E1rmPoint`, `ExerciseTrend` pydantic models.
- `apps/api/app/api/v1/analytics_router.py` — GYM-134 section after the GYM-71 block:
  `_fetch_last_two_session_volumes`, `_fetch_e1rm_trend`, `_trend_to_cache`/`_trend_from_cache`,
  `get_exercise_trend` endpoint.
- `apps/api/tests/test_gym134_exercise_trend.py` — mirrors test_gym71 structure (dedicated
  USER_ET_ID=500013 fixture): volume math, prior-session selection, per-session max Epley e1RM,
  window default-8/52 + 1..52 validation (422 outside), single-session → prev null,
  empty history → nulls/[], per-user isolation, 401 without auth, repeated-call cache path.

SQL approach (GYM-71 discipline): name → exercise_id via the shared RLS-scoped resolver
(resolution miss NOT cached — GYM-99); two sargable day-grouped aggregates on
`idx_training_user_exercise`:
1) `SELECT date::date, SUM(weight*reps) … GROUP BY date::date ORDER BY day DESC LIMIT 2`
   (last + prev session volumes, no window — they are the two most recent sessions regardless);
2) `SELECT date::date, MAX(weight * (1 + reps/30.0)) … AND date >= :window_start GROUP BY date::date
   ORDER BY day ASC` — e1RM computed in SQL; `date::date` only in SELECT/GROUP BY/ORDER BY,
   the window bound is a plain range on the raw timestamp column.
Cache: `make_key(uid, "exercise-trend", muscle=…, exercise=…, weeks=…)` (90 s TTL); GYM-47
mutation invalidation purges `analytics:{uid}:*`, so the new key family is covered automatically
(verified in `bot_router` / `training_history_router` — both call `invalidate_user(uid)`).

Verification (agent sandbox):
- `openapi.yaml` valid OpenAPI 3.1 (`scripts/validate.py`: 39 paths, 43 schemas).
- py_compile green on all touched python; analytics_router imports and registers
  `/analytics/exercise-trend` (checked via FastAPI route table).
- TS regen: web bench `tsc --noEmit` green + 163/163 vitest tests pass (no web source changes).
- **api integration tests WRITTEN but NOT RUN** — they need live Postgres (conftest db_setup);
  pending for operator: run the apps/api pytest suite + EXPLAIN spot-check for index use.

Suggested commit: `Add exercise-trend analytics endpoint with contract and tests`
