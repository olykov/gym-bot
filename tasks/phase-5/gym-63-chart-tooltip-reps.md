---
schema_version: 1
id: GYM-63
title: "apps/web: show reps in the Progress chart tooltip (weight × reps)"
slug: gym-63-chart-tooltip-reps
status: review
priority: low
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T03:00:00Z
start_date: 2026-06-05T03:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: [GYM-57, GYM-62]
blocks: []
related: [GYM-12]
commits: [4b05050229c49dcc801926725669af198051d2e0]
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
- [x] Tooltip shows weight × reps in both By Weight and By Set; build green; plugin invoked.

## Comments

### 2026-06-05T03:00:00Z — operator-reported, in progress
Small tooltip enhancement; the data already has reps (TrainingSet / exercise-progress points).

### 2026-06-04T00:00:00Z — implemented, in review
`frontend-design` plugin invoked before the UI change; kept "Chalk & Iron" + §10.5 (no re-pick).

- **Tooltip:** now renders `{weight}kg × {reps}` plus the full date in BOTH modes, in
  `ExerciseProgressChart.tsx`'s axis-tooltip formatter. Reps reads from each point's `data.reps`;
  aligned the figure to the spec §11.2 format (`100kg × 3`, dropped the stray space before `kg`).
- **By Weight reps carry-through:** `byWeightSeries` now tracks `{weight, reps}` per date instead of
  just the max weight. When picking the max weight it remembers that set's reps; the derived point
  emits `{value: weight, reps}` so the tooltip shows the heaviest set's `weight × reps` for the day.
  Tie rule: replace only on strictly-greater weight (`>`), so the **first-encountered** set at the
  max weight keeps its reps.
- **By Set:** unchanged data path — each point already carried `reps`; it now surfaces in the tooltip.
- §10.5 theming intact: Sora, tabular-nums (`extraCssText`), tooltip `--bg`/`--text`, re-themes on
  `themeChanged` (memo keyed on `themeVersion`). No layout change, no new deps.
- **Build:** `npm run build` (tsc + vite) green — 716 modules, built in ~2.9s (only the pre-existing
  chunk-size advisory, not an error).
- **Needs a live device pass:** hover/tap a point at 360px in Telegram light AND dark to confirm
  tooltip contrast and the `weight × reps` line wrap.
