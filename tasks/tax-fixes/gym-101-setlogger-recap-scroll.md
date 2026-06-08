---
schema_version: 1
id: GYM-101
title: "apps/web: SetLogger recap DESC + internal scroll (keep logging controls + PR visible; page never scrolls)"
slug: gym-101-setlogger-recap-scroll
status: in_progress
priority: high
type: bug-fix
labels: [tax-fixes, frontend, design, ux, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T16:30:00Z
finish_date: null
updated: 2026-06-08T16:30:00Z
epic: tax-fixes
depends_on: []
related: [GYM-69, GYM-99]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-101 — SetLogger recap scroll + keep controls/PR visible

## Problem (live, operator — logged 9 sets, reopened)
1. The today-recap list of already-logged sets grows tall and pushes the main logging controls (steppers,
   Save) DOWN, forcing the whole sheet/page to scroll. Want: recap sorted DESC by set number, older sets
   (1,2,3…) scrolled/collapsed out of view, only the last ~N visible (N = whatever the phone screen
   allows — varies by device). The recap block scrolls INTERNALLY; the logging controls + PR chip stay
   fixed/visible; the page itself never scrolls.
2. On reopen (to log set 10) the PR text is gone — strongly suspected to be the PR chip getting pushed
   below the fold by the tall recap (#1), OR a stale log-context. Ensure the PR chip is visible AND
   actually loads its real value on reopen (investigate: layout vs a stale frontend log-context cache /
   query-key mismatch; fix the root cause — e.g. refetch/invalidate on open or fix key consistency).

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only)
- Restructure SetLogger so: the recap of today's sets is a bounded, INTERNALLY-scrollable block (DESC by
  set#, newest first, capped to the available height ~last few), and the current-set logging area (set#
  header + PR chip + weight/reps steppers + sticky Save) stays in a fixed region that's always visible
  without scrolling the page. Use the §11/§12 primitives + the fixed-height sheet (GYM-74). Auto-advance
  still re-arms the next set in place.
- Verify the PR chip renders with its REAL value on reopen after many sets (not blank). If it's a stale
  log-context, fix it (refetch on open / consistent query key); if it was purely layout, confirm fixed.
- Keep all SetLogger behavior (pre-fill, auto set#, PR-beat, recap w×r from GYM-74, light/dark, reduced-motion).

## Acceptance criteria
- [ ] With many sets, recap is DESC + internally scrollable (last N visible), controls + PR stay visible,
      the page does not scroll; PR chip shows its real value on reopen; plugin invoked; build green.

## Comments

### 2026-06-08T16:30:00Z — task created
Live: 9 sets of face pulls pushed controls down + PR off-screen. Frontend-design plugin mandatory.
