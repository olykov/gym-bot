---
schema_version: 1
id: GYM-69
title: "apps/web: record-training flow (sheet — pick + log set, pre-fill, auto-advance)"
slug: gym-69-record-flow-build
status: done
priority: high
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: 2026-06-05T07:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: [GYM-66, GYM-67, GYM-68]
blocks: []
related: [GYM-64]
commits: [d9171c9900f5eba938680e4b07e5ada5b4ae3b76]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-69 — Record-training flow

## Problem
Build the record flow the center FAB opens, per spec §12.2–12.9 — super smooth, ~1 tap per extra set.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md §12)
- `<RecordSheet>` (controller over the existing `<BottomSheet>`) wired to the GYM-68 FAB; two phases
  (body-swap), BackButton-closes-sheet-first.
- **Phase A `<RecordPicker>`:** fast lane = `GET /analytics/recent-exercises` chips (1 tap); browse by
  muscle (`top-muscles` → `top-exercises?limit=200`, render top ~6 + **"Show all"** client-side expand,
  §12.9); add-inline `+ Muscle` / `+ Exercise` (`POST /muscles`/`POST /exercises`). Empty new-user path
  → add-first-exercise prompt.
- **Phase B `<SetLogger>`:** today recap (`completed-sets` ∪ session), auto set #, two `<Stepper>`s
  pre-filled — same-session last set, else the `recent-exercises` last working set, else PR, else empty;
  PR chip; in-sheet sticky SAVE (§11.4) → `POST /training`; success haptic; **auto-advance re-arms in
  place** (+1 tap/set); PR-beat accent pulse; "← Switch exercise" / "Done".
- Cross-screen invalidation on save-settle / close: summary, activity, completed-sets, personal-record,
  exercise-progress, training days + today (§12.5). Write-error keeps the sheet open, no false recap.
- States/empty/error/light+dark/reduced-motion (§12.6); tokens only; reuse §11 primitives.

## Acceptance criteria
- [ ] FAB opens the sheet; log a set end-to-end (pick → pre-filled → SAVE) and additional sets at ~1 tap;
      Dashboard/Progress/History reflect it; tap-budget (§12.3) met; build green; plugin invoked.

## Comments

### 2026-06-05T06:00:00Z — task created
The heart of GYM-64. Depends on the recent-exercises endpoint (GYM-67) + the FAB (GYM-68).

### 2026-06-04 — built (frontend-design-engineer, `frontend-design` plugin invoked)
Plugin: invoked the `frontend-design` skill before any UI work; applied "Chalk & Iron" +
frontend-spec §12 verbatim (Bebas/Sora, one `--accent`, token-only, reused §11 primitives — did NOT
re-pick the aesthetic).

Components (all under `apps/web/src/components/record/` unless noted; SHA d9171c9):
- `RecordSheet.tsx` — controller over the existing `<BottomSheet>`; two phases by body-swap (NOT
  multi-route); resets to Phase A on close; BackButton closes the sheet first (owned by BottomSheet,
  §11.7); computes `today` via `toISODate`.
- `RecordPicker.tsx` (Phase A) — fast lane `recent-exercises` 1-tap chips (carries
  `{muscle_name, exercise_name, last_weight, last_reps}` into Phase B); browse fallback = muscle
  `<ChipRow>` (top-muscles ∪ /muscles) → exercises **top 6 + "Show all"** client-side expand (§12.9);
  add-inline `+ Muscle` / `+ Exercise` (optimistic via invalidate, auto-select into Phase B); empty
  new-user "ADD YOUR FIRST EXERCISE" prompt (no analytics fan-out on the empty path); read errors
  degrade (browse still usable), not block.
- `SetLogger.tsx` (Phase B) — today recap = `completed-sets` numbers ∪ this-session sets (session =
  full `w×r`, pre-session = `Set n ✓`); auto set # = `max(completed ∪ session)+1`; two pre-filled
  `<Stepper>`s (weight step 2.5 decimal, reps int); PR `--accent` chip; sticky `<SheetSaveButton>` →
  `POST /training`; success haptic; auto-advance re-arms in place (nextSet+1, keep pre-fill) → +1
  tap/set; PR-beat single accent pulse + recap-row flare (behind reduced-motion); "← Switch
  exercise" / "Done".
- `AddInlineField.tsx`, `types.ts` (ChosenExercise).
- `ui/SheetSaveButton.tsx` — extracted the §11.4 sticky Save into one shared component; refactored
  `history/SetEditor.tsx` to reuse it (one sticky-Save style).
- `index.css` — `pr-pulse` + `pr-flare` keyframes, both disabled under prefers-reduced-motion.

Pre-fill priority (§12.3): (1) same-session last set for this exercise; (2) the carried
`recent-exercises` last working set; (3) PR (`personal-record`) as the labelled fallback; (4) empty
+ `--hint`, Save disabled until valid. Auto-advance keeps the just-saved values (gym sets repeat).

Data / hooks (`hooks/useRecord.ts`, `api/analytics.ts`, `api/training.ts`):
`useRecentExercises` (enabled on open), `useCompletedSets`, `usePersonalRecord`, `useCreateMuscle`,
`useCreateExercise`, `useCreateTraining`. Per-exercise reads stay disabled until an exercise is
chosen (empty path fires nothing). Cross-screen invalidation on each save-settle (§12.5):
`["analytics","summary"]`, `["analytics","activity"]`, `["analytics","completed-sets",muscle,exercise]`,
`["analytics","personal-record",muscle,exercise]`, `["analytics","exercise-progress",muscle,exercise]`,
`["training","days"]`, `["training","day",today]`, AND `["analytics","recent-exercises"]`. Write error
keeps the sheet open with an inline "Couldn't save that set — try again", does NOT advance the set #
or append the recap (no false recap).

NavFab wiring: lifted `recordOpen` state into `AppShell`; renders `<RecordSheet>` there and passes
`onRecord={() => setRecordOpen(true)}` to `<BottomNav>` (which already forwards it to `<NavFab>`).

Build: `cd apps/web && npm run build` (tsc + vite) — GREEN (724 modules; pre-existing ECharts
chunk-size warning only, not from this change).

Needs a live-device pass (cannot verify in this env): the actual `POST /training` round-trip + the
§12.5 invalidation refreshing Dashboard/Progress/History; pre-fill correctness across the 4 priority
tiers; the auto-advance feel (+1 tap/set, no scroll-jump); the PR pulse/flare timing; dark-mode
contrast of the `--accent` PR chip and the FAB ring; haptics on real Telegram.
