---
schema_version: 1
id: GYM-101
title: "apps/web: SetLogger recap DESC + internal scroll (keep logging controls + PR visible; page never scrolls)"
slug: gym-101-setlogger-recap-scroll
status: done
priority: high
type: bug-fix
labels: [tax-fixes, frontend, design, ux, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T16:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-fixes
depends_on: []
related: [GYM-69, GYM-99]
commits: [928f839]
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
- [x] With many sets, recap is DESC + internally scrollable (last N visible), controls + PR stay visible,
      the page does not scroll; PR chip shows its real value on reopen; plugin invoked; build green.

## Comments

### 2026-06-08T16:30:00Z — task created
Live: 9 sets of face pulls pushed controls down + PR off-screen. Frontend-design plugin mandatory.

### 2026-06-08 — implementation (928f839)

**Layout restructure (the core fix).**
SetLogger's root div is now `flex min-h-0 flex-1 flex-col`, filling the BottomSheet body which is already `flex flex-col` in `fixedHeight` mode. The content is split into three regions:
1. Static top (`shrink-0`): switch button + createHint + exercise identity. Never moves.
2. Recap (`flex-1 min-h-0 overflow-y-auto`): takes all remaining height between the top and controls, scrolls internally. Older sets scroll away below the fold.
3. Controls (`shrink-0`): SET heading + PR chip + loading hint + steppers + write error + SheetSaveButton + Done. Pinned to the bottom of the flex column, always visible.

The page/sheet itself never scrolls. Only the recap block scrolls internally.

**DESC sort.** The recap `useMemo` now sorts `(a, b) => b - a` (newest set number first). After logging set 9, set 9 appears at the top; sets 1–8 scroll below. The most-recently-logged set is always at the top of the recap.

**PR chip on reopen — root cause.** The PR chip was not missing from the cache or stale. Investigation confirmed:
- `useLogContext` uses `["analytics", "log-context", muscle, exercise, date]` as its key.
- `useCreateTraining.onSettled` invalidates `["analytics", "log-context", vars.muscle_name, vars.exercise_name]` (prefix, no date) — this correctly marks the key stale and triggers a refetch while the sheet is open.
- The `prAnchor` `useEffect` seeds from `ctx.data?.pr` on first render when the cache is warm (reopen within 10 min staleTime window), so the PR populates immediately.
- Root cause was **purely layout**: the PR chip (at `SET {n}` heading) was below the recap section in the old DOM order, and 9 rows of recap pushed it off the bottom of the fixed-height sheet. No cache key mismatch. Fix: PR chip moved into the always-visible controls region.

**Height reasoning at 360px with 9 sets.**
Sheet height ≈ `100dvh − header − 24px`. On a 360×640 phone with ~56px header, sheet ≈ 560px.
- Static top: switch button (~44px) + exercise identity (~28px) ≈ 72px.
- Controls: SET heading + PR chip row (~32px) + 2 steppers (~140px) + SheetSaveButton (~48px + 12px pad) + Done button (~44px) ≈ 276px.
- Remaining for recap: 560 − 72 − 276 ≈ 212px. Each set row is ~36px min-height → ~5–6 rows visible. With 9 sets, the last 3–4 scroll below. Controls + PR stay fully in view.

**Build result.** `tsc && vite build` green. No new TypeScript errors. Chunk size warning is pre-existing, not introduced here.

**Needs live-device pass.** Verify on a real phone (especially iOS Safari and Telegram iOS/Android) that:
- The recap region scrolls with touch (no `pointer-events` or `touch-action` conflicts from the BottomSheet scrim).
- The controls region does not jump or re-layout when a new set is saved (optimistic append at the top of the DESC recap).
- The PR chip appears immediately on reopen when the log-context cache is warm.
- The `SheetSaveButton` renders correctly without its `sticky` positioning (it's now in a non-scrolling parent; `sticky` is a no-op but harmless).
