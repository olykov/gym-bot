---
schema_version: 1
id: GYM-45
title: "apps/web: lazy-load ECharts (code-split the Progress chart)"
slug: gym-45-echarts-code-split
status: in_progress
priority: low
type: refactor
labels: [phase-5, frontend, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T15:35:00Z
start_date: 2026-06-08T22:30:00Z
finish_date: null
updated: 2026-06-04T15:35:00Z
epic: phase-5
depends_on: [GYM-42]
blocks: []
related: [GYM-12]
commits: []
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
- [ ] echarts is in its own async chunk; Dashboard bundle excludes it; build warning gone.

## Comments

### 2026-06-04T15:35:00Z — task created
Perf follow-up flagged during the GYM-42 review. Not blocking the MVP cutover.
