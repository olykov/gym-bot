---
schema_version: 1
id: GYM-104
title: "apps/web: PR chip shows wrong/no PR on reopen (one-shot prAnchor race) — derive effective PR + Show-Hidden polish"
slug: gym-104-pr-chip-race-fix
status: in_progress
priority: critical
type: bug-fix
labels: [tax-fixes, frontend, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T18:30:00Z
start_date: 2026-06-08T18:30:00Z
finish_date: null
updated: 2026-06-08T18:30:00Z
epic: tax-fixes
depends_on: [GYM-101, GYM-103]
related: [GYM-99]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-104 — PR chip race + Show Hidden polish

## Problem (live, prod-investigated — DATA IS SAFE)
Prod verified: Barbell row (id 345) has 58 sets, real PR = 80kg×5; no duplicates; the server (log-context →
`_resolve_exercise_id` by name_key → `_fetch_personal_record`) returns PR=80 correctly. The bug is purely
in the Mini App SetLogger PR-chip logic.

1. **#3 (critical) — wrong/no PR on reopen.** The PR chip is driven by a one-shot `prAnchor` state, seeded
   from the server PR only `if (pr && prAnchor === null)`. On reopen, `prAnchor` starts null; if the user
   saves a set BEFORE log-context resolves, the PR-beat (`beat = prAnchor === null || weight > prAnchor`)
   sets `prAnchor = <session weight>` (e.g. 2.5). The seed effect then never fires (prAnchor ≠ null), so the
   real server PR (80) is lost and the chip shows "PR 2.5kg". Result: PR absent on reopen, then a tiny
   session set wrongly shown as PR.
2. **#1 (polish) — "Show Hidden" expander:** the chevron ">" is glued to the text; add a space.
3. **#2 (bug) — hidden exercises don't surface:** hiding a couple of exercises in Back made them vanish but
   NO "Show Hidden" expander appeared on the exercise step (so they're unrecoverable from the picker).
   Reproduce + fix (the exercise-step expander must list `GET /exercises/hidden?muscle=<name>` items).

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only)
- #3 ROOT FIX: replace the fragile one-shot `prAnchor` with a DERIVED effective PR. The displayed PR =
  the greater of the server PR (`ctx.data.pr`) and the session best weight; the chip shows the server PR
  (with `× reps`) whenever it's the max. A session set only becomes "PR" if it STRICTLY beats the server
  PR. While `ctx.isLoading`, never let a session save claim PR. So even if the user saves 2.5 before
  log-context loads, once it resolves PR shows 80×5 (not 2.5). Keep the PR-beat pulse (fires when a new set
  strictly beats the current effective PR). No timing/race dependence.
- #1: add a space between the chevron and "Show Hidden".
- #2: reproduce hiding exercises in a muscle; ensure the exercise-step Show Hidden expander appears and
  lists the hidden exercises for that muscle (check the useHiddenExercises(muscleName) arg + render
  condition) with Unhide.
- Keep all SetLogger/picker behavior intact.

## Acceptance criteria
- [ ] On reopen with history, the PR chip shows the REAL server PR (e.g. 80kg×5), never a smaller session
      set; #1 spacing fixed; hidden exercises surface in the exercise-step Show Hidden with Unhide; plugin
      invoked; build green.

## Comments

### 2026-06-08T18:30:00Z — task created
Prod-verified data safe + server PR correct; bug is the SetLogger one-shot prAnchor race. Critical.
