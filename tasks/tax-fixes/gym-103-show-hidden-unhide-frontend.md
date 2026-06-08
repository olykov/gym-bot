---
schema_version: 1
id: GYM-103
title: "apps/web: muscle list excludes hidden (freq-ordered visible) + Show Hidden expander + Unhide (muscles & exercises)"
slug: gym-103-show-hidden-unhide-frontend
status: in_progress
priority: high
type: feature
labels: [tax-fixes, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T17:30:00Z
finish_date: null
updated: 2026-06-08T16:30:00Z
epic: tax-fixes
depends_on: [GYM-102]
related: [GYM-83, GYM-99]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-103 — Show Hidden + Unhide

## Problem (live, operator)
- Hiding a muscle (Chest) leaves its TILE in the picker (and long-tap stops working): the picker's muscle
  list UNIONS `top-muscles` (history-based, ignores hidden) with the visible muscles, so a hidden muscle
  lingers via top-muscles. The exercise list (GYM-83 full catalog via visible_exercises) already excludes
  hidden after GYM-99.
- There is no way to see/restore hidden items from the picker.

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only)
- Muscle list = the VISIBLE muscles (the /muscles endpoint, which now excludes hidden), ORDERED by
  top-muscles frequency (use top-muscles only for ordering, NOT as a source that re-adds hidden ones) —
  mirror what GYM-83 did for exercises. A hidden muscle no longer appears as a tile.
- Add a subtle **"Show Hidden"** expander at the BOTTOM of the picker (operator's ask):
  - On the muscle (root) step → lists the user's hidden MUSCLES (GYM-102 `GET /muscles/hidden`).
  - On the exercise step → lists the hidden EXERCISES for that muscle (GYM-102).
  - From the expander, **Unhide** an item (long-tap → Unhide, matching the manage-sheet gesture, OR a clear
    Unhide affordance — designer decides via the plugin) → DELETE .../hidden → it returns to the normal
    list. Keep it unobtrusive (collapsed by default, only shown when there ARE hidden items).
- Also: the manage sheet for a HIDDEN item (if reachable) should offer Unhide. Keep all picker behavior
  (slide-nav, fixed height, manage, add-resolve, keyboard) intact. Update docs/frontend-spec.md.

## Acceptance criteria
- [ ] Hidden muscles no longer linger as tiles; a "Show Hidden" expander lists hidden muscles/exercises
      and unhides them (returns to the list); collapsed when nothing hidden; plugin invoked; build green.

## Comments

### 2026-06-08T16:30:00Z — task created
Depends on GYM-102 (list-hidden). Frontend-design plugin mandatory — operator wants the Show Hidden expander.
