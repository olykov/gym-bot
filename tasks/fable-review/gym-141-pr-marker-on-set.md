---
schema_version: 1
id: GYM-141
title: "History: PR shown on the day but no marker on the actual set inside the day"
slug: gym-141-pr-marker-on-set
status: blocked
priority: high
type: bug-fix
labels: [frontend,design,history,feature]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: null
updated: 2026-06-12T11:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-141 — History: PR shown on the day but no marker on the actual set inside the day

## Problem (operator, on-device review of the Fable batch)
- The day shows a PR badge (has_pr, GYM-136) but inside the day there is NO indication of WHICH
  set/exercise is the PR — the operator sees "PR", opens the day, and can't find what/where it was.
  Add a clear PR marker on the specific set (and/or exercise group) that holds the day's record. Derive
  client-side if the data allows (day sets + the exercise's standing max); if it needs an API/contract
  per-set flag, STOP and flag it (then it goes to core-api). ultrathink + frontend-design plugin.

## Analysis — BLOCKED: requires backend change (STOP per task instructions)

### What the API contract provides
- `TrainingDay` (from `GET /training/days`) has `has_pr: boolean` — day-level, at-least-one exercise.
- `TrainingDayDetail` (from `GET /training/day/{date}`) has exercises with `sets[]`, each set carrying
  `{training_id, set, weight, reps}`. **No `is_pr` flag per set or per exercise group.**
- `GET /analytics/personal-record?muscle&exercise` returns the standing max weight for an exercise,
  but this is a separate endpoint per exercise — N exercises × 1 request = N extra API calls.

### Why client-side derivation is not acceptable
To mark WHICH set is the PR client-side, we would need the standing max weight for each exercise in
the day. That requires one `GET /analytics/personal-record?muscle&exercise` call per exercise in
the day detail — exactly the "heavy client-side aggregation / fetch-full-tables" anti-pattern
forbidden by spec §1 and ARCH §2. A 10-exercise day would issue 10 extra requests on every day-open.

Comparison heuristic (is this set's weight >= all other sets in this exercise?) is NOT sufficient:
`has_pr` is defined as "current all-time max-weight set" (spec + schema comment) — a set can be the
highest of the day but not the standing all-time record, or it may TIE the record. Without the
standing max from the server, a client-side comparison would produce false positives or miss ties.

### Required backend change
The fix needs ONE of:
1. Add `is_pr: boolean` to `TrainingSet` schema — server computes per-set PR flag in
   `GET /training/day/{date}` (one extra JOIN, RLS-scoped same as existing, zero extra client requests).
2. Add `has_pr: boolean` to `TrainingDayExercise` — exercise-group level (less precise but simpler).

Option 1 is preferred (per-set, matches the DayCard `has_pr` granularity). This is a core-api task.

### What needs to happen
- Core API: update `GET /training/day/{date}` to include `is_pr` on each `TrainingSet`.
- API contract: add `is_pr: boolean` to `TrainingSet` schema in `openapi.yaml`; regenerate TS client.
- Frontend: use `set.is_pr` in `SetRow` and `HistoryDay` to render a PR chip beside the set figure.

**Status: BLOCKED on backend. Not implementing client-side — it would violate spec §1.**
