---
schema_version: 1
id: GYM-56
title: "API: summary.current_streak = consecutive WEEKS (not days)"
slug: gym-56-streak-weeks
status: review
priority: medium
type: refactor
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T00:00:00Z
start_date: 2026-06-05T00:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-39]
blocks: []
related: [GYM-12, GYM-58]
commits: [29c92a9]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-56 — Streak in weeks

## Problem
`AnalyticsSummary.current_streak` is consecutive DAYS with training — but nobody trains daily, so it
reads as 1 almost always. The operator wants **consecutive WEEKS** with >=1 training instead.

## Plan
Change the streak computation in `/analytics/summary` (apps/api) to count **consecutive Monday-start
weeks (UTC, matching the rest of the analytics)** with >=1 training, anchored at the current week:
- If the current week has >=1 session, it counts; keep walking back while each prior week has >=1.
- If the current week has none YET, do NOT break the chain mid-week — count consecutive prior weeks
  with sessions (the current week is "in progress"). The chain breaks only at a fully-elapsed week
  with zero sessions.
- Document the exact definition in a `# Reason:` comment. The contract field stays `current_streak:
  integer` (no contract change). Keep it cached + sargable; update the analytics tests.

## Acceptance criteria
- [x] `current_streak` reflects consecutive training-weeks; correct on the seeded fixtures; tests green.

## Comments

### 2026-06-05T00:00:00Z — operator-reported, in progress
Stays UTC for now; per-user timezone is a separate backlog task (GYM-58).

### 2026-06-04T00:00:00Z — implementation complete
Weeks definition: `DATE_TRUNC('week', date)` in Postgres is Monday-start UTC. The streak
is the number of consecutive weeks ending at the current week (each with >=1 session).
Forgiving rule: if the current week has no session yet (in progress), do NOT break the
chain — count consecutive prior weeks that have sessions. The chain breaks only at a
fully-elapsed week with zero sessions. Implemented via `_compute_streak_weeks` and
`_monday_of_week` helpers in `apps/api/app/api/v1/analytics_router.py`. SQL query uses
`GROUP BY DATE_TRUNC('week', date)` with a plain `user_id = :uid` WHERE clause so
`idx_training_user_date` is usable (sargable).

Fixture expected value: conftest seeds rows at `NOW()` (today = 2026-06-04, current week
starts 2026-06-01). Single active week = current week → streak = 1. Unit tests additionally
verify: 3 consecutive weeks → streak 3; gap week → streak 1; forgiving current week →
counts from prev week; stale most-recent → streak 0.

pytest summary: 103 passed, 8 warnings in 8.86s (all tests green including 6 new unit tests
in `TestStreakWeeksUnit` and 2 integration tests in `TestStreakWeeksIntegration`).
