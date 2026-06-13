---
schema_version: 1
id: GYM-153
title: "History PR marker: move out of the figure cluster (numbers shift) + weight-vs-reps PR"
slug: gym-153-history-pr-marker-placement
status: done
priority: medium
type: feature
labels: [frontend, design, history, api, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T06:45:00Z
updated: 2026-06-13T19:30:00Z
start_date: 2026-06-13T19:10:00Z
finish_date: 2026-06-13T19:30:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-141, GYM-136]
commits: [9911337]
tests: [apps/api/tests/test_gym153_pr_kind.py, apps/web/src/components/ui/SetRow.test.ts]
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

## Activation (2026-06-13, operator: "погнали") + pr_kind design
GYM-155 now computes WHICH record a set is. The two PR kinds are MUTUALLY EXCLUSIVE: a
weight PR means the weight is strictly above all prior (or first set), which implies the
weight was never lifted before, so the reps-at-weight branch cannot also fire. So
`pr_kind ∈ {"weight","reps"}` (single value), null when `is_pr` is false. First-ever set =
"weight".

Three coordinated parts (start_date set):
1. **Contract** (api-contract-guardian): add `pr_kind` (nullable, enum weight|reps) to
   `TrainingSet`; regen both clients. Additive, non-breaking. Branch fix/gym-153-contract.
2. **Core API** (core-api-engineer): populate `pr_kind` in `GET /training/day/{date}` from the
   GYM-155 window logic (weight branch → "weight", reps branch → "reps", else null). Tests.
   Branch from the contract branch.
3. **Frontend** (frontend-design + plugin): move the PR marker to the row middle (numbers keep
   their axis, no shift on PR/non-PR); label "Weight PR" / "Reps PR" from `pr_kind`, collapsing
   to just "PR" on narrow rows / small phones; audit + do NOT break other PR usages (DayCard
   day-level badge GYM-136, any shared StatChip). Branch from the contract branch.

Orchestrator owns this task file (agents do not edit it) and closes it after integrating all
three + verifying (real-data pr_kind correctness + visual placement) + deploy.

## Comments

### 2026-06-13T06:45:00Z — filed; deferred to backlog per operator

### 2026-06-13T19:10:00Z — activated; wave 1 (contract) launched

### 2026-06-13T19:30:00Z — done (9911337)
Three waves integrated: contract pr_kind, core-api populate (validated on real data: bench 50x10='reps', weight records='weight'), frontend marker→middle (figure 0px shift, Weight/Reps PR labels, narrow→'PR'). Day-level badge unaffected. Gate: web 209 tests + build + lint; api py_compile; core 493 tests.
