---
schema_version: 1
id: GYM-141
title: "History: PR shown on the day but no marker on the actual set inside the day"
slug: gym-141-pr-marker-on-set
status: done
priority: high
type: feature
labels: [frontend,design,history,feature,api,api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: 2026-06-12T20:30:00Z
updated: 2026-06-12T20:30:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [28ba3fa, 2434084]
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

## Plan (unblocked — backend + frontend)
Per the design-agent analysis: `TrainingSet` carries no PR info and a correct all-time-PR marker can't be
derived client-side. So:
1. **Contract** (api-contract-guardian): add `is_pr: boolean` to `TrainingSet`; regen clients.
2. **Core API** (core-api): compute `is_pr` in `GET /training/day/{date}` — a JOIN flagging the set(s) that
   equal the caller's current all-time max weight for that exercise (zero extra client requests). Tests.
3. **Frontend** (frontend-design + plugin): render a PR chip/marker on the flagged set (`SetRow`/HistoryDay),
   on-spec; this lands AFTER GYM-143 (sheet layout) so it sits in a correct layout.

## Comments

### 2026-06-12T09:00:00Z — unblocked with a plan
Reframed from blocked to a 3-step backend+frontend task. Awaiting operator approval to launch (after GYM-143).

### 2026-06-12 — contract step done (api-contract-guardian)
Added `is_pr: boolean` (required) to the `TrainingSet` schema in `packages/api-contract/openapi.yaml`
and regenerated both clients (`make validate` + `make gen`): the Python model
(`clients/python/gym_api_client/models.py` → `TrainingSet.is_pr: bool`, required) and the TS type
(`clients/typescript/schema.ts` → `TrainingSet.is_pr: boolean`, gitignored) both carry it. Additive,
non-breaking (server will always populate it). On branch `fix/gym-141-contract` — NOT merged.
Remaining for `done`: (2) core-api computes `is_pr` in `GET /training/day/{date}`; (3) frontend PR chip
on the flagged set (`SetRow`/HistoryDay), after GYM-143. Status stays `backlog`.

### 2026-06-12T19:51:15Z — backend is_pr implemented (core-api, commit 28ba3fa on fix/gym-141-142-impl)
`GET /training/day/{date}` now computes `is_pr` server-side for every set.

Approach: a `pr` CTE aggregates `MAX(weight) AS max_weight` per `exercise_id` across the caller's
FULL training history (`WHERE user_id = :uid`, no date filter). The CTE is joined to the per-day
rows; `is_pr = (t.weight = pr.max_weight)`. RLS is applied by the DB session (GUC context) for
both the CTE and the day query — no additional `user_id` filter is needed beyond the fail-closed
RLS policy, though the defence-in-depth `WHERE user_id = :uid` is retained in both CTEs.

Semantics: "current all-time max" (not "was a PR when logged"). Ties — including multiple sets on
the same day — all receive `is_pr=True`. A heavier set logged later moves the flag to every row at
the new max on any day.

Branch: `fix/gym-141-142-impl`. Tests in `apps/api/tests/test_gym141_142_day_detail.py`:
  - test_set_at_alltime_max_is_pr_true
  - test_lighter_set_is_pr_false
  - test_ties_all_flagged
  - test_pr_on_different_day_flags_todays_equal_set
  - test_cross_user_pr_isolation
  - test_is_pr_field_present_in_response

Full suite 460 passed, 0 failed, 0 skipped (real postgres:16, Docker up).
Remaining step: (3) frontend PR chip on SetRow/HistoryDay. Status stays `backlog` until frontend ships.

### 2026-06-12T20:30:00Z — frontend PR chip shipped (frontend-design-engineer, branch fix/gym-141-chip)
Chip design: a `<StatChip>` "PR" badge (same component as the DayCard day-level badge, GYM-136) rendered
trailing beside `<SetFigure>` in `<SetRow>` when `set.is_pr === true`. This closes the visual loop:
"this day has a PR" (DayCard chip) → "THIS set is it" (SetRow chip — identical language).

Placement: the trailing section of `<SetRow>` is now a `flex shrink-0 items-center gap-2` cluster —
`<SetFigure>` + optional `<StatChip>`. The chip renders ONLY on PR rows; non-PR rows are layout-identical
to before (no shift, no extra space). The chip gets a single one-shot accent-pulse on appear
(`animate-pr-pulse` keyframe: scale 0.88 → 1.08 → 1, opacity 0 → 1, 320ms ease-out-soft), guarded
by `motion-reduce:animate-none` per spec §9.4.

Token changes:
- `apps/web/src/styles/tokens.css`: added `@keyframes pr-pulse` and `@utility animate-pr-pulse` (Tailwind 4
  CSS-first, no config file change needed).
- `apps/web/src/components/ui/StatCard.tsx`: `StatChip` now accepts an optional `className` prop so callers
  can attach animation classes without coupling motion details to the primitive.
- `packages/api-contract/openapi.yaml`: added `is_pr` to `TrainingSet` (required, boolean) — this is the
  contract step merged into this branch since `fable-integ` didn't include it yet.

Files changed:
- `packages/api-contract/openapi.yaml` (added is_pr to TrainingSet schema)
- `apps/web/src/components/ui/SetRow.tsx` (import StatChip; wrap trailing in flex cluster; conditional chip)
- `apps/web/src/components/ui/StatCard.tsx` (StatChip accepts className)
- `apps/web/src/styles/tokens.css` (pr-pulse keyframe + utility)
- `apps/web/src/components/record/derive.test.ts` (fixture updated: is_pr: false)
- `apps/web/src/components/record/usePickerData.test.ts` (fixtures updated: is_pr: false)

Green gate: tsc zero errors, vite build clean, eslint 0 warnings, 198/198 tests pass.
frontend-design plugin invoked at session start.

