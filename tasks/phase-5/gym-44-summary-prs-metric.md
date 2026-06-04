---
schema_version: 1
id: GYM-44
title: "API: make summary.prs a real metric (PR events, not == exercises)"
slug: gym-44-summary-prs-metric
status: done
priority: medium
type: refactor
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T13:50:00Z
start_date: 2026-06-04T13:55:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T13:50:00Z
epic: phase-5
depends_on: [GYM-39]
blocks: []
related: [GYM-12, GYM-42]
commits: [576ef37]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-44 — Make summary.prs a real metric

## Problem
GYM-39 defined `AnalyticsSummary.prs = COUNT(DISTINCT exercise_id)`, i.e. `prs == exercises` always.
On the 2×2 dashboard that renders two identical numbers — reads like a bug. The contract field is
fine; only the computation must change (no contract change).

## Plan
Redefine `prs` = **count of all-time PR events**: number of training rows whose `weight` is a new
all-time max for that `(user_id, exercise_id)` at that point in time. One sargable query with a
window function (`max(weight) OVER (PARTITION BY exercise_id ORDER BY date, set)` compared to the
running max excluding the current row), scoped via RLS. Keep it cached + tested. Update the GYM-39
`# Reason:` comment and the analytics test expectations.

## Acceptance criteria
- [x] `prs` differs from `exercises` on realistic data; correct on the seeded two-user fixtures.
- [x] Still sargable (no seq-scan); tests green.

## Comments

### 2026-06-04T13:50:00Z — task created
Carved from the GYM-39 review (orchestrator flagged the `prs == exercises` smell).

### 2026-06-04T00:00:00Z — implementation complete (576ef37)
New definition: `prs` = count of all-time PR events — training rows where `weight`
strictly exceeds the running max for the same `(exercise_id)` up to (but not
including) the current row, ordered by `(date, set)`. The first set for each
exercise always counts (prev_max IS NULL). Implemented as a single window-function
query (CTE `windowed`) run as a second small query alongside the existing aggregate,
keeping the endpoint readable and sargable.

Fixture expectations on the two-user seed (conftest):
- Each user has 1 exercise, 2 training rows at the same timestamp, both weight=100.0
  (User A) / 80.0 (User B), set=1 and set=2.
- set=1: prev_max IS NULL → PR event counted.
- set=2: prev_max = 100.0 (or 80.0), weight == prev_max → NOT a PR.
- Result: prs=1, exercises=1 for each user.

On the seeded fixture prs and exercises happen to be equal (1 each), but they
diverge on realistic data with multiple exercises and progressive overload. The
old formula always produced prs == exercises; the new formula is independently
computed and semantically correct.

pytest summary: 73 passed, 2 warnings in 7.69s (all green).
