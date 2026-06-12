---
schema_version: 1
id: GYM-136
title: "Dashboard: 'vs last week' volume/sets comparison + PR-day markers on History DayCards"
slug: gym-136-dashboard-week-compare
status: review
priority: low
type: feature
labels: [frontend, api, dashboard, history, progression]
assignee: agent
model: claude
reporter: oleksii
created: 2026-06-12T10:45:00Z
start_date: 2026-06-12T18:35:00Z
finish_date: null
updated: 2026-06-12T18:55:00Z
epic: progression
depends_on: []
blocks: []
related: [GYM-134, GYM-44]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-136 — Weekly comparison + PR-day markers (Phase 3)

## Problem
Concept doc 03 §4.3. Progression is visible per-set (GYM-130) and per-exercise (GYM-133/135)
but not per-week, and History gives no signal which days mattered (PR days).

## Solution (sketch — refine when Phase 1/2 effects are measured)
- Dashboard card "THIS WEEK vs LAST": volume + sets totals with deltas (likely a small
  `GET /analytics/week-compare?tz` — contract-first, mirrors GYM-134 style).
- History `DayCard`: an accent dot/`PR` micro-chip on days containing a PR (extend the
  `TrainingDay` contract with `has_pr: bool` or derive server-side in /training/days).
- Scope deliberately loose: re-spec against actual Phase 1 feedback before starting.

## Acceptance criteria (refined at implementation, wave 7d)
- [x] `GET /analytics/week-compare?tz` → `WeekCompare {this_week, last_week}` of
      `WeekStats {sets, volume}`; Monday-start calendar weeks in `tz` (UTC default,
      summary's tz convention); zeros for empty weeks; 90s analytics cache
      (GYM-47 invalidate_user covers it); sargable 2-week range query
      (AT TIME ZONE only in SELECT/GROUP BY, never WHERE).
- [x] Dashboard renders a compact THIS WEEK card under SummaryCards, above
      ActivityGrid: `{sets} сетов · {volume} kg` (Bebas tabular inline) + delta
      line vs last week in the GYM-130 visual language (accent ▲ up / hint ▼ down,
      zero deltas omitted — never "▲ 0"). First-ever week → totals without delta
      line. Both weeks zero → renders nothing. New-user empty path never mounts
      the card → no query fired. Loading → SkeletonCard.
- [x] `TrainingDay.has_pr: boolean` in the contract; `/training/days` computes it
      via a per-exercise max-weight CTE + `BOOL_OR(weight = max_weight)`.
      Semantic: **current max** — "day holds the current weight PR of an exercise"
      (not was-PR-at-the-time); a later heavier set moves the marker; ties mark
      every tying day.
- [x] History DayCard shows a tiny accent `PR` chip (reused StatChip) beside the
      date heading when `has_pr`; no layout shift for non-PR days.
- [x] Invalidation: `weekComparePrefix` added to `useCreateTraining` onSettled and
      `useTraining.invalidateAfterMutation`; `has_pr` rides the existing
      `daysPrefix` invalidation.
- [x] All new UI strings via the catalog (en+ru; ru uses «сеты», not «подходы»).
- [ ] Integration tests executed against live Postgres (written, NOT run — operator).
- [ ] Real-device Telegram check of the card + PR chips; EXPLAIN check of the
      has_pr CTE on prod-sized data pending.

## Comments

### 2026-06-12T10:45:00Z — task created
Phase 3 placeholder by design. Overload-streak from doc 03 §4.4 is intentionally NOT a task
(operator decision #4: deferred until Phase 1 impact is measured).

### 2026-06-12T18:55:00Z — implemented (agent wave 7d)
Restrained v1 of both halves, GYM-71/134 discipline throughout.

**Files — Part A (week-compare):**
- `packages/api-contract/openapi.yaml` — `GET /analytics/week-compare` (ActAsUser +
  TimezoneQuery, `WeekCompare`/`WeekStats` schemas)
- `apps/api/app/schemas/schemas.py` — `WeekStats`, `WeekCompare`
- `apps/api/app/api/v1/analytics_router.py` — `_week_compare_bounds` (Monday anchors in tz,
  local-midnight→UTC range bounds), `_fetch_week_buckets` (one grouped query over the 2-week
  range, AT TIME ZONE only in SELECT/GROUP BY), `get_week_compare` (90s cache)
- `apps/web/src/api/analytics.ts` — `fetchWeekCompare` (+ `WeekCompare`/`WeekStats` types)
- `apps/web/src/api/queryKeys.ts` — `weekCompare()` (tz-suffixed) + `weekComparePrefix`
- `apps/web/src/hooks/useAnalytics.ts` — `useWeekCompare`
- `apps/web/src/components/dashboard/weekCompareModel.ts` (+`.test.ts`) — hidden /
  first-week / compare modes, delta rounding
- `apps/web/src/components/dashboard/WeekCompareCard.tsx` — the card (Skeleton on load,
  null on error/hidden)
- `apps/web/src/pages/Dashboard.tsx` — card mounted on the has-data branch only
- `apps/web/src/hooks/useRecord.ts` + `useTraining.ts` — `weekComparePrefix` invalidation
- `apps/web/src/i18n/messages.ts` — `weekCompare.*`, `weekDelta.*` (en+ru, «сеты»)
- `apps/web/src/api/queryKeys.test.ts` — key shape + prefix-contract additions

**Files — Part B (has_pr):**
- `packages/api-contract/openapi.yaml` — `TrainingDay.has_pr` (required, semantic documented)
- `apps/api/app/schemas/schemas.py` — `TrainingDay.has_pr: bool`
- `apps/api/app/api/v1/training_history_router.py` — per-exercise max-weight CTE +
  `BOOL_OR(t.weight = pr.max_weight)` in `/training/days`
- `apps/web/src/components/ui/DayCard.tsx` — accent `PR` StatChip beside the date heading

**Tests:** `apps/api/tests/test_gym136_week_compare.py` (gym134 structure; own users
500014–500017; week math, Monday-rollover under `Etc/GMT-14` with test-side zoneinfo
expectation, empty→zeros, isolation, 401/422, has_pr: standing max / PR-moved-by-later-day /
sub-max / multi-exercise / empty) — **WRITTEN, NOT RUN** (needs live Postgres; operator runs).

**Semantic decision (has_pr):** current-max — the day holds the CURRENT all-time max-weight
set of some exercise ("day holds the current weight PR of an exercise"). Chosen over
"was a PR at the time it was logged" for v1 simplicity; consequence: a later heavier set
moves the marker off the old day, ties mark every tying day. Documented in the contract
description and schemas.

**Verification:** openapi 3.1 valid (40 paths, 45 schemas); both clients regenerated
(datamodel-codegen per Makefile flags; openapi-typescript@7); py_compile + FastAPI
route-table import OK (`/api/v1/analytics/week-compare` present); web bench tsc + eslint
(0 warnings) + vitest **185 passed** (was 177, +8) + vite build — all green.
Pending: integration tests on live Postgres; EXPLAIN of the has_pr CTE; real-device check.

**Suggested commits** (split cleanly API/web):
1. `Add week-compare endpoint and has_pr to training days` — packages/api-contract/*,
   apps/api/*
2. `Add dashboard week comparison card and PR day chips` — apps/web/*
