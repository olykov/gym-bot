---
schema_version: 1
id: GYM-71
title: "API: implement /analytics/log-context (completed-sets + last-session + PR)"
slug: gym-71-log-context-api
status: backlog
priority: high
type: feature
labels: [phase-5, api, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T08:00:00Z
epic: phase-5
depends_on: [GYM-70]
blocks: [GYM-72]
related: [GYM-39, GYM-47]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-71 — API: log-context

## Problem
Implement the combined set-logger context in one cached, RLS-scoped read.

## Plan
`GET /analytics/log-context?muscle&exercise&date` in apps/api (analytics_router), `get_principal` auth:
- `completed_sets` — distinct set numbers on `date` for this exercise (= existing completed-sets logic).
- `last_session_sets` — the sets of the MOST RECENT PRIOR session (the latest `date::date` < today, or
  latest overall if none today) for this exercise: `[{set, weight, reps}]` ordered by set. (e.g. find
  `max(date::date)` for the exercise excluding today, return that day's sets.)
- `pr` — the personal record (= existing personal-record logic) `{weight, reps, date}` or null.
Resolve muscle/exercise by name (RLS-scoped). Sargable (idx_training_user_exercise/idx_training_user_date,
GYM-59). Cache via the analytics cache (key includes muscle/exercise/date); GYM-47 mutation invalidation
covers it. Tests: completed_sets correctness, last_session = the right prior day's sets, pr, isolation,
no-history → empty/null. `EXPLAIN` confirms index use.

## Acceptance criteria
- [ ] log-context returns the 3 parts correctly per-user; sargable; cached; tests green.

## Comments

### 2026-06-05T08:00:00Z — task created
One endpoint replaces 3 Phase-B roundtrips (the §3 latency fix) + powers last-session pre-fill.
