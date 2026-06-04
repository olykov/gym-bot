---
schema_version: 1
id: GYM-62
title: "apps/web: Progress pickers by frequency + open on top exercise's By Weight chart"
slug: gym-62-progress-default-frequency
status: backlog
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: [GYM-60, GYM-61]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-62 — Progress: frequency pickers + non-empty default

## Problem
Progress opens on an empty pick-screen and the pickers are alphabetical. Operator wants them ordered
by HIS training frequency and the page to open straight on the By Weight chart of his most-frequent
exercise.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- Muscle picker → `GET /analytics/top-muscles` (frequency desc). Exercise picker →
  `GET /analytics/top-exercises?muscle=&limit=<all>` (frequency desc). Replace the alphabetical
  list-endpoint calls in Progress.
- **Default on mount:** auto-select `top-muscles[0]` → load its exercises → auto-select
  `top-exercises[0]` → render the **By Weight** chart immediately (no empty pick-screen). Most-frequent
  exercise in the most-frequent muscle ≈ the user's top exercise.
- **Empty state:** a brand-new user with no trainings (empty top-muscles) keeps the existing
  `<EmptyState>` ("log a set in the bot…"), no auto-select, no extra queries.
- Keep the By Weight | By Set toggle (GYM-57) and the design consistent; tokens only.

## Acceptance criteria
- [ ] Progress opens on the By Weight chart of the most-frequent exercise; pickers ordered by my
      frequency; new-user empty state intact. Build green; plugin invoked.

## Comments

### 2026-06-05T01:00:00Z — task created
Mostly wiring to the new endpoints + the auto-select-on-mount default.
