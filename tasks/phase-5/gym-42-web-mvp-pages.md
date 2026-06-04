---
schema_version: 1
id: GYM-42
title: "apps/web: MVP pages — dashboard activity-grid + summary, exercise progress"
slug: gym-42-web-mvp-pages
status: review
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T13:55:00Z
finish_date: 2026-06-04T15:30:00Z
updated: 2026-06-04T15:30:00Z
epic: phase-5
depends_on: [GYM-39, GYM-41]
blocks: []
related: [GYM-12]
commits: [b35fa66]
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

### 2026-06-04T15:30:00Z — MVP pages built (commit b35fa66)
Implemented by frontend-design-engineer. The `frontend-design` skill was invoked
before any UI work (aesthetic applied, not re-picked: "Chalk & Iron" §9).

Components built (all token-only, inside the existing `<AppShell>`):
- Dashboard: `<SummaryCards>` (2×2 StatCards, Bebas count-up via new `useCountUp`,
  skipped on cache hit + under reduced-motion; PRs is the `--accent` hero with the
  StatChip) + `<ActivityGrid>` (Monday-first 26-week window, chalk→iron `--accent`
  ramp, today ring, per-cell "N sets on <date>" tooltip, staggered ink-in). Pure
  `activityGridModel.ts` owns the Monday-first matrix + level bucketing + window.
- Progress: `<ChipRow>` powering dependent Muscle→Exercise pickers (≥44px, accent
  pill) + `<ExerciseProgressChart>` (echarts-for-react, one line series per set,
  weight plotted + reps in tooltip).
- Charts: single `echartsTheme.ts` reading live CSS vars (series → `--accent`
  ramp toward `--hint`, dash style beyond the 4-color cap; axes/text `--hint`/
  `--text` Sora tabular-nums; tooltip `--bg`/`--text`, not default white),
  re-themed on Telegram `themeChanged` via new `useThemeVersion`.
- States first-class (§10.4): layout-matching skeletons on `isLoading`,
  `<ErrorState>`+retry on `isError`, `<EmptyState>` for new user (no extra
  queries) and empty exercise series; dependent picker/progress queries stay
  disabled until inputs exist.
- New hooks: `useAnalytics` (summary/activity/muscles/exercises/progress via
  TanStack Query), `useCountUp`, `useThemeVersion`. New analytics fetchers typed
  by the `@api-contract` schema.

Activity-grid 360px fit: CSS flex-fill, not fixed-px cells — 26 columns each
`flex:1` + `aspect-square`, so columns divide the available card width and the
window always fits with NO horizontal scroll on any phone (full-year deferred).
Dark-mode empty cells use the brightened `--grid-empty-bg` token (white@4% over
`--bg`) for visibility.

Build: `npm run build` (tsc + vite) PASSES — 704 modules, ~2.9s. Only the
pre-existing ECharts chunk-size warning (no new deps). Needs a real Telegram/
browser visual pass for dark-mode line+tooltip contrast and the 360px grid.
