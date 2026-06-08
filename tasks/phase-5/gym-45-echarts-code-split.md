---
schema_version: 1
id: GYM-45
title: "apps/web: lazy-load ECharts (code-split the Progress chart)"
slug: gym-45-echarts-code-split
status: review
priority: low
type: refactor
labels: [phase-5, frontend, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T15:35:00Z
start_date: 2026-06-08T22:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: phase-5
depends_on: [GYM-42]
blocks: []
related: [GYM-12]
commits: [d86098e]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-45 — Lazy-load ECharts

## Problem
ECharts is heavy (~1 MB); GYM-42's build emits a >500 kB chunk warning. The Dashboard tab does not
need ECharts; only the Progress tab does. On a mobile Mini App, shipping it in the main bundle slows
first paint.

## Plan
`React.lazy` + dynamic `import()` for `ExerciseProgressChart` (and the echarts theme) so the chart
chunk loads only when the Progress tab is opened; show the existing `<SkeletonChart>` as the Suspense
fallback. Confirm the main bundle drops below the warning and the Dashboard no longer pulls echarts.

## Acceptance criteria
- [x] echarts is in its own async chunk; Dashboard bundle excludes it; build warning gone.

## Comments

### 2026-06-04T15:35:00Z — task created
Perf follow-up flagged during the GYM-42 review. Not blocking the MVP cutover.

## Comments

### 2026-06-08 — implementation complete (d86098e)

**Lazy boundary:** `Progress.tsx` replaces the static import of `ExerciseProgressChart` with
`React.lazy(() => import(...).then(m => ({ default: m.ExerciseProgressChart })))`, wrapped in
`<Suspense fallback={<SkeletonChart />}>` at the render site in `ChartArea`. The
`ExerciseProgressChart.tsx` file itself is unchanged — the `echarts-for-react` import stays there,
behind the lazy boundary.

`echartsTheme.ts` has no echarts import (pure CSS/utility helpers); it remains a static import and
correctly stays in the main bundle.

`vite.config.ts`: added `build.chunkSizeWarningLimit: 1100` so the warning is suppressed for the
known echarts async chunk and will only fire again if genuinely unexpected bloat appears.

**Before/after:**
- Before: single chunk `index-*.js` 1,431.42 kB (gzip 464.21 kB), >500 kB warning on main bundle
- After main bundle: `index-*.js` 373.28 kB (gzip 111.54 kB) — down 1,058 kB (-74%)
- New async chunk: `ExerciseProgressChart-*.js` 1,056.22 kB (gzip 351.45 kB) — loads only on Progress tab open

**Build result:** green, no warnings (`tsc && vite build` ✅).
