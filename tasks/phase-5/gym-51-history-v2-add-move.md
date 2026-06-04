---
schema_version: 1
id: GYM-51
title: "History v2: add a set retroactively + move a set (date/exercise)"
slug: gym-51-history-v2-add-move
status: backlog
priority: low
type: feature
labels: [phase-5, frontend, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-51 — History v2: add + move sets

## Problem
v1 (GYM-49) does view + edit weight/reps + delete. The operator wants, as the NEXT step, the ability
to add a set retroactively and move a set to another day/exercise.

## Plan (v2, after v1 ships)
- Add a set within a day/exercise (`POST /training` with an explicit date) — needs the create path to
  accept a date (today's create is `NOW()`); contract + API tweak.
- Move a set: change its `date` and/or `exercise_id` (a PUT extension or a dedicated endpoint) +
  cache invalidation. UX in the day-detail/editor.

## Acceptance criteria
- [ ] Add-set and move-set work end-to-end with isolation + cache invalidation.

## Comments

### 2026-06-04T18:00:00Z — task created
Deferred from the History plan (KISS); operator confirmed it's the planned next step after v1.
