---
schema_version: 1
id: GYM-42
title: "apps/web: MVP pages — dashboard activity-grid + summary, exercise progress"
slug: gym-42-web-mvp-pages
status: backlog
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: [GYM-39, GYM-41]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-42 — apps/web: MVP pages

## Problem
Build the two MVP screens on the shell, consuming the analytics endpoints.

## Plan (owner: frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- **Dashboard** (tab 1): GitHub-style **`<ActivityGrid>`** (from `/analytics/activity`) + **2×2
  `<SummaryCards>`** (exercises / sets / PRs / streak, from `/analytics/summary`). Grid uses the
  chalk→iron `--accent` ramp (spec §9.3, NOT GitHub green), Monday-first, "today" ring; **MVP window
  = last ~26 weeks (6 mo), fits 360px with NO horizontal scroll** (full-year deferred). PRs stat is
  the `--accent` hero (count-up).
- **Progress** (tab 2): `<MusclePicker>`→`<ExercisePicker>` (existing list endpoints) +
  **`<ExerciseProgressChart>`** (ECharts) weight/reps series (from `/analytics/exercise-progress`),
  one series per set, responsive, legible at 360px. **ECharts themed via the `echartsTheme(cssVars)`
  contract (spec §10.5)** — series mapped to `--accent` ramp, axis/text to `--hint`/`--text` in Sora
  tabular-nums, tooltip in `--bg`/`--text` (not default white), re-themes on `themeChanged`. Multi-
  set distinguished by dash style beyond ~4 series (don't rely on color alone).
- **States are first-class, not afterthoughts (spec §10.4):** every query renders a **`<Skeleton>`**
  matching final layout on `isLoading` (no spinners / layout shift), **`<ErrorState>`** + retry on
  `isError`, and **`<EmptyState>`** for new users (no trainings) and empty exercise series. The
  empty path must NOT fire extra queries (ARCH §2 lesson).
- All data via the generated TS client + TanStack Query (cache/loading/error, sane TTL). No fetch
  storms; pickers don't refetch the world on every change.
- Every screen inside `<AppShell>`; tokens only; mobile-first; light+dark; page-load stagger reveal.

## Acceptance criteria
- [ ] Both screens populated for an existing user; graceful **`<EmptyState>`** for a new one (and no
      extra queries on the empty path).
- [ ] Loading = skeletons matching layout (no spinner/jump); error = inline retry, no raw error dump.
- [ ] Activity grid = last ~26 weeks (6 mo), fits 360px **with no horizontal scroll** in v1,
      Monday-first, accent ramp (not green); **dark-mode empty cells visible**. (Full-year = deferred.)
- [ ] Charts responsive + legible at 360px, themed to tokens, **dark-mode line + tooltip contrast
      verified**, multi-set distinguishable without color-only; cross-user data never visible (RLS).
- [ ] `prefers-reduced-motion` respected (no count-up / ink-in when set).
- [ ] docs/frontend-spec.md §7 checklist passes; `frontend-design` skill was invoked.

## Comments

### 2026-06-04T09:00:00Z — task created
Faithful to the old site's two core views, but cached/indexed and design-consistent.
