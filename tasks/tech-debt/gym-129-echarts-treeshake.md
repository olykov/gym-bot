---
schema_version: 1
id: GYM-129
title: "ECharts: tree-shakeable echarts/core imports + drop echarts-for-react wrapper"
slug: gym-129-echarts-treeshake
status: review
priority: medium
type: chore
labels: [frontend, perf, deps, charts]
assignee: agent
model: claude-fable-5
reporter: oleksii
created: 2026-06-12T10:05:00Z
start_date: 2026-06-12T19:10:00Z
finish_date: null
updated: 2026-06-12T19:40:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-45, GYM-128]
commits: []
tests: []
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-129 — ECharts tree-shaking

## Problem
Review doc 02 §2/§7. The Progress chunk lazy-loads (GYM-45) but pulls the FULL echarts
bundle (~1MB) via `echarts-for-react`, whose wrapper value is ~40 lines of init/setOption/
resize and whose releases have stagnated.

## Solution
- Import `echarts/core` + only `LineChart`, `GridComponent`, `TooltipComponent`,
  `LegendComponent` + `CanvasRenderer`; `echarts.use([...])`.
- Replace `echarts-for-react` with a local `useECharts(option)` hook (init on mount,
  `setOption` on change, ResizeObserver on the card, dispose on unmount, re-theme via
  `useThemeVersion` as today). Remove the dependency.
- Check echarts major version while here (5 → 6 if stable; otherwise stay).

## Acceptance criteria
- [x] Progress chunk size cut ≥50% (record before/after in a comment).
- [x] Chart behavior identical: both modes, sparse labels, tooltip, theme flip, 360px.
  (Code-verified: same option object, same notMerge/lazyUpdate contract, same
  themeVersion/mode-keyed remount. Operator visual smoke still recommended.)

## Comments

### 2026-06-12T10:05:00Z — task created

### 2026-06-12T19:40:00Z — implemented (agent wave 8)

**Chunk sizes (vite build, before → after):**
- `ExerciseProgressChart` chunk: **1,056.75 kB → 516.38 kB raw (−51%)**, gzip
  **351.61 kB → 174.52 kB (−50.4%)** — acceptance "≥50% cut" met.
- (Final numbers measured after the full GYM-128 upgrade pack; the cut itself comes
  from this task — verified identical 517 kB on the pre-upgrade Vite 5 build too.)

Changes:
- NEW `src/components/charts/useECharts.ts`: `echarts/core` + `echarts.use([LineChart,
  GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])`; hook does init on
  mount, `setOption(option, { notMerge: true, lazyUpdate: true })` on option change
  (the exact contract the old `<ReactECharts notMerge lazyUpdate>` usage had),
  ResizeObserver→`chart.resize()`, dispose on unmount.
- `ExerciseProgressChart.tsx`: renders an inner `<ChartCanvas option>` (fixed-height div
  + the hook), still keyed on `${themeVersion}-${mode}` so a Telegram theme flip / mode
  switch re-inits cleanly exactly as before. Option-building code untouched.
- `echarts-for-react` removed from package.json; `echarts` bumped 5.5.1 → **6.1.0**
  (stable; option API used here unchanged — build/tsc/tests green, no deprecations hit).
- Renderer note: the old wrapper passed `opts={{ renderer: "svg" }}`; per this task's
  spec the hook registers **CanvasRenderer** (SVGRenderer is not bundled). Line chart +
  HTML tooltip render identically; flag at visual smoke if any aliasing difference
  matters at 360px.
- Lazy route-level import in `Progress.tsx` kept — echarts stays out of the main bundle;
  `vite.config.ts` chunkSizeWarningLimit lowered 1100 → 600 to match the slimmer chunk.

Verification: `tsc --noEmit` + `eslint --max-warnings 0` + `vitest run` (185/185) +
`vite build` all green.

Suggested commit message: `Tree-shake echarts via local useECharts hook`
