---
schema_version: 1
id: GYM-56
title: "API: summary.current_streak = consecutive WEEKS (not days)"
slug: gym-56-streak-weeks
status: in_progress
priority: medium
type: refactor
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T00:00:00Z
start_date: 2026-06-05T00:00:00Z
finish_date: null
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-39]
blocks: []
related: [GYM-12, GYM-58]
commits: []
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
- [ ] `current_streak` reflects consecutive training-weeks; correct on the seeded fixtures; tests green.

## Comments

### 2026-06-05T00:00:00Z — operator-reported, in progress
Stays UTC for now; per-user timezone is a separate backlog task (GYM-58).
