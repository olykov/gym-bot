---
schema_version: 1
id: GYM-100
title: "apps/web: fix broken add-exercise modal + Hide action for own items + refresh log-context on add/resolve"
slug: gym-100-add-modal-hide-own-logctx-refresh
status: in_progress
priority: critical
type: bug-fix
labels: [tax-fixes, frontend, design, ux, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T15:00:00Z
start_date: 2026-06-08T15:30:00Z
finish_date: null
updated: 2026-06-08T15:00:00Z
epic: tax-fixes
depends_on: [GYM-99]
related: [GYM-85, GYM-98]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-100 — Add-modal fix + Hide-own + log-context refresh

## Problem (live, operator)
1. The add-exercise inline field renders BROKEN/janky — the input isn't even visible at first; typing
   shows a badly-rendered field. A real UI regression (likely the keyboard-inset GYM-98 × the GYM-85 hint
   placement). Reproduce + fix.
2. Long-tap on an OWN exercise should offer **Hide** as well as Rename/Move/Delete (operator decision —
   an own item with history can't be deleted, so Hide is the only way to declutter it). Verify
   Rename/Move/Delete are all present too.
3. After add→resolve (existing/unhidden), the SetLogger must show the EXISTING PR/history (not look new).
   With GYM-99 (name_key resolution + no negative cache), the frontend must INVALIDATE the log-context
   (and any per-exercise analytics) for that exercise on the create/resolve mutation so SetLogger refetches
   fresh server data instead of a stale (10-min staleTime) empty.

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only)
- #1: reproduce the broken add field; fix its rendering (layout/visibility under the keyboard-inset +
  hint). The field + submit must be fully visible and clean on a ~360px device.
- #2: add a **Hide** action to the manage sheet for OWN exercises (and own muscles if applicable), wired to
  `PUT /exercises/{id}/hidden` (GYM-99 now supports own). Keep Rename + Move + Delete. Ensure the offer-hide
  fallback on a 409-history delete still works.
- #3: in `useCreateExercise`/`useCreateMuscle` onSuccess (the add/resolve path), invalidate
  `["analytics","log-context", muscle, exercise, ...]` (and completed-sets/personal-record if separately
  keyed) for the resolved exercise so the SetLogger loads the real PR/history. Verify an existing exercise
  re-added shows its PR immediately.
- Keep all GYM-74/82/85/90/98 behavior intact; update docs/frontend-spec.md as needed.

## Acceptance criteria
- [ ] Add-exercise field renders cleanly (visible input + submit). Own items show Hide + Rename/Move/Delete.
      Re-adding an existing exercise shows its real PR/history immediately (not "new"). Plugin invoked;
      build green.

## Comments

### 2026-06-08T15:00:00Z — task created
Depends on GYM-99 (name_key resolution + no negative cache + hide-own API). Frontend-design plugin mandatory.
