---
schema_version: 1
id: GYM-155
title: "PR label wrong: is_pr/has_pr flag every max-weight set (constant-weight exercises always PR)"
slug: gym-155-pr-label-correctness
status: todo
priority: high
type: bug-fix
labels: [api, core-api, history, pr, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T14:50:00Z
updated: 2026-06-13T14:50:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-141, GYM-136, GYM-133]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-155 — PR label is computed incorrectly across the app

## Problem (operator, confirmed in prod DB)
History shows "PR" on sets that are NOT personal records. Operator's Pull-Up (exercise 355,
user 2107709598): EVERY set is at 1.00 kg (bodyweight marker); all-time best is 1 kg × 10
reps (2025-07-10). Today's 1 kg × 7 and 1 kg × 5 are below the rep record, yet History marks
them PR.

## Root cause
Both PR flags use `weight = max_weight` over the user's whole history for the exercise:
- `has_pr` (day) in `GET /training/days` — `BOOL_OR(t.weight = pr.max_weight)`.
- `is_pr` (set) in `GET /training/day/{date}` — `t.weight = pr.max_weight`.
So any set at the all-time max weight is flagged, including repeats; a constant-weight exercise
(bodyweight) has weight == max_weight on EVERY set → every set/day flagged PR (~38 sets here).

Meanwhile the RECORD flow (`apps/web/.../derive.ts` `resolvePrBeat`, GYM-133) already computes
PR correctly: strict weight beat OR strict reps-at-weight beat OR strict e1RM beat. The History
flags are the inconsistent, wrong ones.

## Proposed fix (PENDING operator approval on semantics)
Define a set as a PR (temporal — "was a PR when logged", the conventional badge), matching the
operator's definition "max weight OR max reps at a weight":
A set is_pr if, vs all the user's EARLIER sets for that exercise (ordered by date, set):
1. weight strictly greater than every prior weight (or it is the first set), OR
2. the weight was lifted before AND reps strictly greater than the best prior reps at that
   exact weight.
(e1RM dimension: present in the record flow; for the History label keep to the operator's two
dimensions unless we decide to align fully.)
`has_pr` (day) = BOOL_OR(is_pr) over the day. Both endpoints fixed = app-wide consistency.
Implementation: SQL window functions (running max weight / max reps-at-weight as of each set,
partitioned by user+exercise [+weight for reps]). No api-contract change (fields stay boolean).

Validation against the operator's data: 2025-07-10 1 kg × 10 = reps PR; today's 7 and 5 = not
a PR. Pull-Up should show ONE rep-PR historically, none today.

## Plan
core-api-engineer implements the window-function computation in both endpoints + tests (incl. a
constant-weight / bodyweight case and a reps-PR case). Verify against the operator's real data
shape. Orchestrator re-verifies.

## DECISION (operator-approved, 2026-06-13)
- **Option A**: History PR = weight PR OR reps-at-weight PR. **NO e1RM** dimension in the
  History label (e1RM stays where the operator likes it — the Progress page + the SetLogger
  trend sparkline, both unchanged).
- **First set ever of an exercise = PR** (weight PR, no prior source) — keep, as the record
  flow already does.
- Temporal semantics ("was a PR when logged"), ordered by (date, set).

## Comments

### 2026-06-13T14:50:00Z — investigated (prod DB), root cause found, fix plan pending approval

### 2026-06-13T15:25:00Z — approved Option A; delegating to core-api
