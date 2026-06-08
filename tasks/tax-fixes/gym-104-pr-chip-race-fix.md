---
schema_version: 1
id: GYM-104
title: "apps/web: PR chip shows wrong/no PR on reopen (one-shot prAnchor race) — derive effective PR + Show-Hidden polish"
slug: gym-104-pr-chip-race-fix
status: review
priority: critical
type: bug-fix
labels: [tax-fixes, frontend, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T18:30:00Z
start_date: 2026-06-08T18:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-fixes
depends_on: [GYM-101, GYM-103]
related: [GYM-99]
commits: [047ee4e]
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

### 2026-06-08T00:00:00Z — implemented (047ee4e)

**#3 — PR chip race (critical):** Replaced the fragile one-shot `prAnchor` useState + seed
`useEffect` pattern with a `useMemo`-derived `effectivePR` computed each render from `serverPR`
(ctx.data.pr) and `sessionBestWeight` (max weight across sessionSets). The effective PR weight is
`max(serverPR.weight, sessionBestWeight)`; reps are shown only when the server PR is the source
(session sets have no reps). This eliminates the race entirely: no matter when `ctx` resolves, the
real server PR wins once it arrives — a 2.5kg session set saved before log-context loaded cannot lock
in a wrong anchor, because there is no anchor state to lock. Reopening Barbell row will show
"PR 80kg × 5" as soon as ctx resolves. The PR-beat pulse fires when a new set strictly exceeds
`effectivePR.weight`. The `setPrAnchor` state and seed effect are removed; no timing dependence
remains. Build: tsc + vite green.

**#1 — Show Hidden spacing:** `ShowHiddenExpander` trigger button changed from `gap-1.5` to `gap-2`
and an explicit `{" "}` space added before the label text, so the rotated `›` chevron has visible
separation from "Show hidden muscles/exercises".

**#2 — Exercise-step Show Hidden expander invisible after hide:** Root cause: `invalidateElementLists`
(called by `useHideExercise`, `useHideMuscle`, `useDeleteExercise`, move, rename, etc.) did not
invalidate `["exercises", "hidden"]`. After hiding an exercise, the hidden-exercises cache (seeded as
`[]` on first exercise-step visit) stayed stale within its 5-minute `staleTime`, so
`hiddenExercises.data.length` remained 0 and `ShowHiddenExpander` never rendered. Fix: added
`qc.invalidateQueries({ queryKey: ["exercises", "hidden"] })` to `invalidateElementLists` — covers
the partial key prefix so all per-muscle hidden caches are refreshed on any element-list mutation.

**Needs live-device pass:**
- Open Barbell row on a real device after a cold open (ctx not yet resolved); log 2.5kg before ctx
  arrives; confirm PR chip shows 80kg × 5 once ctx resolves, NOT 2.5kg.
- Hide one exercise in Back, re-open the exercise step for Back, confirm "Show hidden exercises"
  appears; long-press hidden tile, confirm Unhide works and tile returns to the visible grid.
- Confirm "Show hidden" trigger has a visible space between the chevron and text.
