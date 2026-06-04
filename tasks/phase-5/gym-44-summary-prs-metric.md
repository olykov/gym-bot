---
schema_version: 1
id: GYM-44
title: "API: make summary.prs a real metric (PR events, not == exercises)"
slug: gym-44-summary-prs-metric
status: todo
priority: medium
type: refactor
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T13:50:00Z
start_date: null
finish_date: null
updated: 2026-06-04T13:50:00Z
epic: phase-5
depends_on: [GYM-39]
blocks: []
related: [GYM-12, GYM-42]
commits: []
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
- [ ] `prs` differs from `exercises` on realistic data; correct on the seeded two-user fixtures.
- [ ] Still sargable (no seq-scan); tests green.

## Comments

### 2026-06-04T13:50:00Z — task created
Carved from the GYM-39 review (orchestrator flagged the `prs == exercises` smell).
