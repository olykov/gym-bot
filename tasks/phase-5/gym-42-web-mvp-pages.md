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
- **Dashboard** (tab 1): GitHub-style **activity grid** (from `/analytics/activity`) + summary cards
  (exercises / sets / PRs / streak, from `/analytics/summary`). Empty-state for new users.
- **Progress** (tab 2): muscle→exercise pickers (existing list endpoints) + **ECharts** weight/reps
  series (from `/analytics/exercise-progress`), responsive, multi-set.
- All data via the generated TS client + TanStack Query (cache/loading/error). No fetch storms.
- Every screen inside `<AppShell>`; tokens only; mobile-first; light+dark.

## Acceptance criteria
- [ ] Both screens populated for an existing user; graceful empty-state for a new one.
- [ ] Charts responsive + legible at 360px; cross-user data never visible (RLS).
- [ ] docs/frontend-spec.md §7 checklist passes; `frontend-design` skill was invoked.

## Comments

### 2026-06-04T09:00:00Z — task created
Faithful to the old site's two core views, but cached/indexed and design-consistent.
