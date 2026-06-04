---
schema_version: 1
id: GYM-63
title: "apps/web: show reps in the Progress chart tooltip (weight × reps)"
slug: gym-63-chart-tooltip-reps
status: in_progress
priority: low
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T03:00:00Z
start_date: 2026-06-05T03:00:00Z
finish_date: null
updated: 2026-06-05T03:00:00Z
epic: phase-5
depends_on: [GYM-57, GYM-62]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-63 — Reps in the Progress chart tooltip

## Problem
The Progress chart tooltip shows the weight but not the reps. The operator wants to tap a point and
see e.g. "100kg × 3" — the weight AND the reps for that point.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- In `apps/web/src/components/progress/ExerciseProgressChart.tsx` (+ `charts/echartsTheme.ts` if the
  tooltip formatter lives there), make the tooltip show `{weight}kg × {reps}` plus the date.
- **By Set:** points already carry `reps` — include them in the tooltip.
- **By Weight:** the derived `byWeightSeries` takes the MAX weight per date; carry the **reps of that
  max-weight set** through the derivation so the tooltip can show the reps of the heaviest set that day
  (if there are ties, the first/any is fine — document the choice).
- Keep §10.5 token theming (Sora, tabular-nums, `--bg`/`--text` tooltip), light+dark, no layout change.

## Acceptance criteria
- [ ] Tooltip shows weight × reps in both By Weight and By Set; build green; plugin invoked.

## Comments

### 2026-06-05T03:00:00Z — operator-reported, in progress
Small tooltip enhancement; the data already has reps (TrainingSet / exercise-progress points).
