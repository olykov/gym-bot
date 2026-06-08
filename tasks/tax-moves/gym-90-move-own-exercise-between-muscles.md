---
schema_version: 1
id: GYM-90
title: "Move OWN exercise between muscles (long-tap → Move to muscle; own-only; dedup vs target) — startable now"
slug: gym-90-move-own-exercise-between-muscles
status: in_progress
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T10:00:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-moves
depends_on: []
blocks: []
related: [GYM-89]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-90 — Move own exercise between muscles

## Problem
A user may misplace an exercise (e.g. Squat under Chest). They need to move it to the right muscle —
independent of the taxonomy work and can ship NOW (operator: "можно вот сейчас уже сделать").

## Scope (layers): contract + API + frontend
- API: move an OWN exercise to another muscle (set its muscle); own-only; dedup against the target muscle
  by name_key (GYM-84). 403 on canonical/global (those are GYM-91's policy).
- Frontend (design plugin): long-tap on an exercise → manage sheet gains "Move to another muscle" → pick
  target muscle from the list → moved. Keep the existing manage-sheet design language.

## Acceptance
- [ ] Move an own exercise to another muscle from the manage sheet; own-only; dedup vs target; tests +
      build green.
