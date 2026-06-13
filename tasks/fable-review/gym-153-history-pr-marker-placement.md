---
schema_version: 1
id: GYM-153
title: "History PR marker: move out of the figure cluster (numbers shift) + weight-vs-reps PR"
slug: gym-153-history-pr-marker-placement
status: backlog
priority: medium
type: feature
labels: [frontend, design, history, api, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T06:45:00Z
updated: 2026-06-13T06:45:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-141, GYM-136]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-153 — History PR marker placement + weight/reps distinction

## Problem (operator)
In a History day, a set's PR chip is appended to the RIGHT of the `{weight}×{reps}` figure
(`SetRow.tsx`: trailing cluster `[SetFigure | StatChip]` under `justify-between`). The chip
widens the cluster and pushes the numbers LEFT → asymmetry vs non-PR rows. The marker should
NOT sit after the numbers.

## Desired (design via frontend-design plugin — DEFERRED, backlog)
1. Move the PR marker into the MIDDLE of the row (free space between `SET N` and the figure)
   so the numbers keep their right-aligned axis and do NOT shift on PR vs non-PR rows.
2. Distinguish **weight-PR vs reps-PR**. Backend currently exposes only `is_pr` = all-time
   max WEIGHT (GYM-141). A reps-PR needs a new flag (api-contract + core-api), like is_pr was
   added. Design plugin decides the visual + whether/how to show the distinction.
3. **Responsive label:** on a narrow row / small phone where the middle has little space,
   render just "PR" instead of "Weight PR"/"Reps PR" (graceful truncation of the label).

## Constraints (operator)
- MUST NOT break the existing PR banner/badge anywhere else it is used (e.g. DayCard day-level
  PR badge GYM-136, and any other StatChip "PR" usages) — audit all usages before changing the
  shared component; prefer a SetRow-local treatment over mutating the shared chip if needed.
- Non-PR rows must remain layout-identical.

## Plan
Deferred to a later iteration (operator: "не берём в эту итерацию, оставь в беклоге").
When picked up: frontend-design-engineer + plugin proposes the marker design + responsive
label; if weight/reps distinction is wanted, api-contract-guardian + core-api-engineer add a
reps-PR flag first. Verify headless dark + realistic insets + the narrow-width fallback.

## Comments

### 2026-06-13T06:45:00Z — filed; deferred to backlog per operator
