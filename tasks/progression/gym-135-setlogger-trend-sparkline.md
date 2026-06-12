---
schema_version: 1
id: GYM-135
title: "SetLogger: e1RM sparkline + trend chip next to the PR target (where the curve is going)"
slug: gym-135-setlogger-trend-sparkline
status: review
priority: low
type: feature
labels: [frontend, record, progression, ux]
assignee: agent
model: claude
reporter: oleksii
created: 2026-06-12T10:40:00Z
start_date: 2026-06-12T18:12:00Z
finish_date: null
updated: 2026-06-12T18:28:00Z
epic: progression
depends_on: [GYM-134]
blocks: []
related: [GYM-130, GYM-133]
commits: []
tests: ["apps/web/src/components/record/trend.test.ts", "apps/web/src/api/queryKeys.test.ts"]
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-135 — SetLogger trend sparkline

## Problem
Concept doc 03 §4.2. While logging, the user sees the PR and the last session (after
GYM-130) but not the direction of travel — "is this exercise trending up over weeks?".

## Solution
- A micro-sparkline (inline SVG polyline, ~64×20px, NO chart library in the sheet) of
  `e1rm_trend` from `GET /analytics/exercise-trend` next to the SET/PR heading row, plus a
  tiny trend chip `▲ 8w` / `→` in `--hint`/accent.
- Query fired on Phase B entry alongside log-context (same staleTime discipline); skeleton
  = a flat hint line; absent/short history → render nothing (no empty noise).
- Strictly secondary visual weight — must not compete with SET N / steppers / Save.
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin; spec §12.3 note.

## Acceptance criteria
- [x] Sparkline renders for exercises with ≥3 sessions in the window; hidden otherwise. (Code + unit tests; on-device visual check pending.)
- [x] No added latency to Phase B interactivity (steppers usable before trend resolves — TrendSparkline owns its own query; render-independent). (Device check pending.)

## Comments

### 2026-06-12T10:40:00Z — task created

### 2026-06-12T18:28:00Z — implemented (agent wave 7c)

**Files:**
- `apps/web/src/api/analytics.ts` — `fetchExerciseTrend(muscle, exercise, weeks, signal?)` + `ExerciseTrend`/`SessionVolume`/`E1rmPoint` type re-exports (GYM-134 contract).
- `apps/web/src/api/queryKeys.ts` — `analytics.exerciseTrend(muscle, exercise, weeks)` + `exerciseTrendPrefix(muscle?, exercise?)` invalidation contract.
- `apps/web/src/hooks/useRecord.ts` — `useExerciseTrend(muscle, exercise)` (`TREND_WEEKS = 8`, SESSION staleTime/gcTime, enabled only with both names); `useCreateTraining` onSettled now also invalidates `exerciseTrendPrefix(muscle, exercise)` (a saved set changes the trend).
- `apps/web/src/hooks/useTraining.ts` — `invalidateAfterMutation` adds the broad `exerciseTrendPrefix()` (history weight edits/deletes/moves change e1RM history).
- `apps/web/src/components/record/trend.ts` — NEW pure helpers: `buildSparklineGeometry` (normalize → polyline points + end-dot), `trendDirection` (±1% flat band), `MIN_TREND_POINTS = 3`.
- `apps/web/src/components/record/trend.test.ts` — NEW, 14 unit tests (<3 points → null, viewBox bounds, y inversion, flat-series mid-line, end-dot, duplicate dates, threshold boundaries, zero-first-value edge).
- `apps/web/src/components/record/TrendSparkline.tsx` — NEW: 64×20 inline SVG polyline (`stroke: var(--accent)`, width 1.5, 2px end-dot, no axes) + tiny `▲/▼/→ {weeks}w` chip; SVG/glyphs aria-hidden, group exposes `role="img"` + full-sentence aria-label.
- `apps/web/src/components/record/SetHeadingRow.tsx` — NEW: the SET/PR heading row extracted from SetLogger (file-size split) now hosting the trend group.
- `apps/web/src/components/record/SetLogger.tsx` — heading row swapped for `<SetHeadingRow>`; 500 → 483 lines.
- `apps/web/src/i18n/messages.ts` — `trend.up/down/flat` (+ `*Aria` screen-reader sentences), en+ru (`8w` / `8 нед`).
- `apps/web/src/api/queryKeys.test.ts` — exerciseTrend shape + both prefix forms + no collision with `exercise-progress` prefix.

**Decisions / deviations:**
- Spec said "skeleton = a flat hint line"; chose to render NOTHING while loading (and on error/short history) — a placeholder that may resolve to nothing is flicker; absence is the quiet state. Noted in the component docblock.
- Trend group placed LEFT of the PR chip in the heading row (small gap); PR chip stays the dominant right anchor; heading is the flexible truncating child at 360px.
- Sparkline x-spacing is index-based, not date-based — it is a direction glyph, not a chart; duplicate session dates become a non-issue by construction.
- Trend chip i18n: `▲ {weeks}w` / `▼` / `→` — unicode geometric figures (same family as the GYM-130 delta badges), not emojis. Up = `text-accent`, down/flat = `text-hint` (no red — same "don't punish a light day" rule as deltas).
- `useExerciseTrend` lives inside `TrendSparkline` (mounted only in Phase B), so the query fires on Phase B entry alongside log-context and never blocks stepper interactivity. Invalidation (save / history edit) refetches the active query despite the 10-min staleTime — normal TanStack semantics.
- Static SVG, no animation → reduced-motion N/A.

**Verification:** bench (`/tmp/bench/apps/web`): `npx tsc --noEmit` PASS, `npm run lint` (max-warnings 0) PASS, `npm run test` 177/177 PASS (163 pre-existing + 14 new), `npm run build` PASS. On-device visual check (360px crowding, dark/light) pending.

**Suggested commit:** `Add e1RM trend sparkline to SetLogger heading`
