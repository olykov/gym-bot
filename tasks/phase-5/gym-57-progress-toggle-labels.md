---
schema_version: 1
id: GYM-57
title: "apps/web: Progress By Weight|By Set toggle + sparse x-axis; Dashboard label tweaks"
slug: gym-57-progress-toggle-labels
status: review
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T00:00:00Z
start_date: 2026-06-05T00:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: [GYM-42, GYM-56]
blocks: []
related: [GYM-12]
commits: [1160af8]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-57 — Progress toggle + axis + Dashboard labels

## Problem
Operator iteration on the live Mini App:
- **2b** Progress only shows per-set lines; the DEFAULT should be the overall weight trend ("how my
  bench grew"). Add a top toggle **By Weight** (default) | **By Set**.
- **2a** With many points the x-axis dates are a cramped mess; thin them and rely on the tooltip.
- **1b** The Dashboard PRs card label is unclear → rename to **"PRs set"**.
- **1c** `current_streak` is now WEEKS (GYM-56) → label the Streak card so it reads as weeks.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- **Toggle** (segmented control, top of Progress, ≥44px, accent active, token-only):
  - **By Weight (default):** ONE line = max weight per session/date over time, DERIVED client-side from
    the existing `/analytics/exercise-progress` data (flatten all sets' points → group by date → max
    weight). The strength-over-time trend.
  - **By Set:** the current behavior (one line per set).
- **X-axis (2a):** show only a few sparse labels (e.g. first/last + a couple), full date in the tooltip
  (§10.5 token theming kept). Legible at 360px regardless of point count.
- **Dashboard (1b):** rename the PRs `<StatCard>` label to **"PRs set"** (keep the accent hero + chip).
- **Streak (1c):** label the Streak card so the number reads as weeks (e.g. "Streak" + a "wks" unit or
  "Week streak") — value comes from the API (now weeks via GYM-56).

## Acceptance criteria
- [x] Progress defaults to By Weight (single trend line); toggle to By Set works; x-axis not cramped,
      date in tooltip; PRs card reads "PRs set"; Streak reads as weeks. Build green; plugin invoked.

## Comments

### 2026-06-05T00:00:00Z — operator-reported, in progress
By Weight derives from the existing endpoint — no API change. Toggle labels: By Weight | By Set.

### 2026-06-04T00:00:00Z — implemented (frontend-design-engineer), commit 1160af8
Invoked the `frontend-design` plugin before the UI work; applied the committed "Chalk & Iron"
direction + docs/frontend-spec.md (§9.3 accent/token rules, §10.3/§10.5 chart contract). All changes
confined to `apps/web/` (the concurrent `apps/api/` edits were left untouched in the working tree).

- **2b — By Weight | By Set toggle.** New token-only `<SegmentedControl>` (≥44px segments,
  `--accent-weak` track, active = `--bg` pill + `--accent` text) at the top of Progress. State is in
  `Progress.tsx`, default **By Weight**. By Weight derives ONE series client-side from the existing
  `/analytics/exercise-progress` response — flatten all sets' points, group by date, take the max
  weight per date, sort ascending (no API change). By Set keeps one line per set (legend shown only in
  By Set; hidden for the single-line trend).
- **2a — sparse x-axis.** Chart now plots on a shared `category` axis of the distinct session dates;
  `sparseLabelIndices()` thins labels to ~5 evenly-spaced `DD MMM` ticks (first + last + interior)
  regardless of point count, applied to BOTH modes. Full date stays in the tooltip
  (`toLocaleDateString`). §10.5 token theming kept (Sora, `--hint`/`--text`, tabular-nums, `--bg`
  tooltip). Removed the old per-week `maxInterval`/two-tier time-axis labels.
- **1b — PRs label.** Dashboard PRs `<StatCard>` label "PRs" → **"PRs set"** (accent hero + PR chip
  unchanged).
- **1c — Streak label.** Streak `<StatCard>` label "Streak" → **"Week streak"** so the GYM-56 weeks
  value reads as weeks. Value source unchanged (`summary.current_streak`).

Build: `cd apps/web && npm run build` (tsc + vite) **passes** — 716 modules, built in ~3s; the only
warning is the pre-existing ECharts chunk-size note (not from this change).

Needs a live visual pass on a device: By Weight single-line trend shape, axis legibility at 360px with
many points, tooltip date in both light/dark, and the segmented-control active contrast in dark mode.
