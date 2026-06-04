---
schema_version: 1
id: GYM-65
title: "Design: spec §12 — 5-item nav + center FAB + smooth record-training flow (ultrathink, plugin)"
slug: gym-65-record-flow-design
status: done
priority: high
type: research
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T04:00:00Z
start_date: 2026-06-05T04:00:00Z
finish_date: 2026-06-05T06:00:00Z
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: [GYM-64]
blocks: []
related: [GYM-12]
commits: [37e3fe8]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-65 — Record-flow design (spec §12)

## Problem
Need a concrete, buildable design for: (a) the 5-item bottom nav with a raised center "+", and (b) a
super-smooth record-training flow — proposed via the frontend-design plugin before any build.

## Plan
Design-agent (frontend-design plugin, ultrathink) appends `docs/frontend-spec.md` §12 "Record training":
- **Nav:** Dashboard · Progress · [+] · History · Profile (stub). Center = elevated `--accent` circular
  CTA (distinct shape), opens the record sheet (not a route); sliding indicator skips the center; fits
  §2/§9 shell + safe areas. Profile = stub route/empty-state.
- **Record flow (smooth):** recents/frequent exercises first (1-tap) + muscle browse fallback + add
  inline; in-context set logging with weight/reps PRE-FILLED (last set / PR), auto next set#, big
  steppers + in-sheet sticky Save (§11.4), Save→haptic→auto-advance→repeat; PR-beat celebration.
- States/empty/error/reduced-motion; reuse §11 BottomSheet/Stepper primitives; note API additions
  (recent-exercises, last-set pre-fill) vs MVP-with-existing.
- Orchestrator reviews + shows the operator before build.

## Acceptance criteria
- [x] §12 appended (nav + record flow), concrete + buildable; plugin invoked; API needs flagged.

## Comments

### 2026-06-05T04:00:00Z — task created
Proposal only — no app code. Operator approves the UX before the build wave.

### 2026-06-05T05:30:00Z — §12 design proposal complete (review)
Invoked the `frontend-design` plugin (Chalk & Iron, §9), worked in ultrathink. Appended
`docs/frontend-spec.md` **§12 "Record training (nav + log flow)"** — DESIGN ONLY, no app code.

- **§12.1 nav:** 5-item bar `Dashboard · Progress · [+] · History · Profile`; new `<NavFab>` =
  raised circular `--accent` (Chalk & Iron orange-red) center ACTION (opens the record sheet, not a
  route); sliding indicator measured over the 4 route tabs, skips the center; Profile = stub
  `<EmptyState>` route, slot only. Shell/safe-area contract preserved.
- **§12.2–12.3 flow:** one `<BottomSheet>`, two phases (pick → log) with a body-swap. Fast lane =
  frequency-ranked 1-tap exercise chips; muscle→exercise browse fallback; add-inline. Set logger
  pre-fills weight/reps (same-session last set → else PR anchor), auto set-#, two big `<Stepper>`s,
  in-sheet sticky SAVE (§11.4, not the Telegram MainButton), success haptic, auto-advance (re-arm
  in place, same pre-fill, +1 tap/set), PR-beat accent pulse.
- **Tap budget:** open=1; first set of a frequent exercise +2; each extra set **+1**. Full
  3×4 workout ≈16 taps vs the bot's 60 picks.
- **§12.4 primitives:** `<NavFab>`, `<RecordSheet>`, `<RecordPicker>`, `<SetLogger>`,
  maybe `<SheetSaveButton>`, `<ProfileStub>` — all compositions of existing BottomSheet/Stepper/
  Chip/ChipRow/Card/SetRow/EmptyState. No new library.
- **§12.5–12.6 states + cross-screen invalidation** (summary/activity/personal-record/
  exercise-progress/days/today) on save-settle; loading/empty/error/light+dark/reduced-motion.
- **§12.7 API:** MVP fully buildable on existing endpoints (POST /training, top-muscles/-exercises,
  completed-sets, personal-record, max-reps, muscles/exercises CRUD). Flagged 2 nice-to-have
  additions as a SEPARATE task: `GET /analytics/recent-exercises` (one ordered read +
  true recency + last weight/reps → the buttery pre-fill) and `GET /analytics/last-set`.
- **§12.8 gaps/risks:** tap-budget, pre-fill correctness (labelled PR anchor, always editable),
  set-number race, fat-finger FAB, safe-area with the raised FAB (Container bottom pad += FAB lift),
  add-inline dups, recap honesty, cross-screen staleness, BackButton ownership, "--accent is orange".

Proposal awaiting operator approval before the build wave (GYM-64).

### 2026-06-05T05:35:00Z — linked commit; mark review
§12 design committed as `37e3fe8` (docs/frontend-spec.md + this task file only — no app code, not
pushed). Status → review for operator sign-off.
