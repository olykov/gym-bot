---
schema_version: 1
id: GYM-102
title: "Contract+API: list hidden muscles/exercises for the user (powers Show Hidden) + confirm hide-own muscle"
slug: gym-102-list-hidden-api
status: in_progress
priority: high
type: feature
labels: [tax-fixes, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T17:00:00Z
finish_date: null
updated: 2026-06-08T16:30:00Z
epic: tax-fixes
depends_on: []
blocks: [GYM-103]
related: [GYM-99]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-102 — List hidden (API) for Show Hidden

## Problem
A user can hide muscles/exercises (GYM-99) but there is no way to LIST what's hidden, so the frontend
can't offer a "Show Hidden → Unhide" affordance. Need a list-hidden read.

## Plan (api-contract-guardian → core-api-engineer; no migration)
- Add read endpoints to list the caller's hidden items:
  - `GET /muscles/hidden` → the muscles this user has hidden (Muscle[]).
  - `GET /exercises/hidden?muscle=<name>` (and/or unscoped) → the exercises this user has hidden, scoped
    to a muscle for the picker. (Decide the cleanest shape; mirror existing list endpoints + auth.)
- Confirm hiding an OWN muscle works end-to-end (GYM-99 made visibility exclude hidden for own + global;
  verify the hide endpoint accepts an own muscle). Unhide already exists (DELETE .../hidden).
- Regen both clients. Tests: hidden lists return exactly the user's hidden items; empty when none.

## Acceptance criteria
- [ ] list-hidden endpoints for muscles + exercises; hide-own muscle confirmed; clients regenerated;
      tests + full apps/api suite green.

## Comments

### 2026-06-08T16:30:00Z — task created
Powers the Show Hidden / Unhide UX (GYM-103).
