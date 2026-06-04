---
schema_version: 1
id: GYM-57
title: "apps/web: Progress By Weight|By Set toggle + sparse x-axis; Dashboard label tweaks"
slug: gym-57-progress-toggle-labels
status: in_progress
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T00:00:00Z
start_date: 2026-06-05T00:00:00Z
finish_date: null
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-42, GYM-56]
blocks: []
related: [GYM-12]
commits: []
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
- [ ] Progress defaults to By Weight (single trend line); toggle to By Set works; x-axis not cramped,
      date in tooltip; PRs card reads "PRs set"; Streak reads as weeks. Build green; plugin invoked.

## Comments

### 2026-06-05T00:00:00Z — operator-reported, in progress
By Weight derives from the existing endpoint — no API change. Toggle labels: By Weight | By Set.
