---
schema_version: 1
id: GYM-74
title: "apps/web: picker slide-nav (muscle→exercise push) + fixed-height sheet + today recap w×r fix"
slug: gym-74-record-picker-slide-nav
status: done
priority: high
type: feature
labels: [phase-5, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T11:00:00Z
start_date: 2026-06-05T11:00:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-72]
blocks: []
related: [GYM-64, GYM-69]
commits: [bd9b607, c94ea78]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-74 — Picker slide-nav + fixed-height sheet + today-recap w×r fix

## Problem (operator feedback on live v2)
1. **Today recap loses values on reopen/Continue.** Sets logged this session show `Set 1 — 100kg × 8`,
   but after closing+reopening or entering via Continue they collapse to `Set 1 ✓` (checkmark only) —
   because the recap then reads `completed_sets` (set NUMBERS only) instead of the actual weight/reps.
2. **Muscle→exercise should be a horizontal screen transition, not the sheet growing.** Today picking a
   muscle expands the sheet (exercises appear below → height jumps). Operator wants a navigation PUSH:
   tap a muscle → muscles slide LEFT out, that muscle's exercises slide IN from the right, with a Back
   affordance. Plus: the sheet a bit TALLER and FIXED height (no jump between steps), muscle tiles a
   bit BIGGER, layout that handles variable-length muscle names + custom muscles, and the sheet must
   NEVER overlap the app header. Animation fast, intuitive, non-flickering — user always knows where a
   view came from and how to go back.

## Plan (frontend-design-engineer — MANDATORY: invoke `/frontend-design:frontend-design` and ultrathink the layout; keep the app's consistent Chalk & Iron design; tokens only, no new lib)

### #1 — today recap shows real w×r after reopen/Continue
- The recap of today's sets for the chosen exercise must show `Set n — {weight}kg × {reps}`, not
  `Set n ✓`, regardless of whether the sheet was just opened, reopened, or entered via Continue.
- Source today's sets-with-values from `GET /training/day/{today}` (already fetched/prefetched for the
  Continue tile; its `TrainingDayExercise.sets` carry `{set, weight, reps}`) filtered to the chosen
  exercise. Merge with this-session sets (session takes precedence for a just-saved set). NO API change.
- Auto set# still = `max(today's set numbers ∪ session) + 1`. Pre-fill logic (GYM-72 last_session_sets)
  unchanged.

### #2 — slide-nav picker + fixed taller sheet (ultrathink the layout via the plugin)
- **Two in-sheet steps as a horizontal PUSH** (muscle list → exercise list), e.g. a translateX track:
  picking a muscle slides muscles out left and the exercises in from the right; a Back control (and the
  Telegram BackButton, §11.7) slides back. Fast (~180–240ms), eased, reduced-motion → instant swap,
  no flicker. The Continue tile + faint divider stay on the muscle (root) step.
- **Fixed sheet height across both steps** so nothing jumps — pick a height that fits the typical tile
  grid AND **never overlaps the app header** (respect the AppShell fixed header + safe-area top inset;
  the sheet's max height must stay below the header). The frontend designer decides the exact
  height/inset math via the plugin.
- **Bigger muscle tiles** in a **responsive grid** that tolerates variable-length labels + custom
  muscles (operator unsure on columns — designer decides: e.g. an auto-fit grid, not a hardcoded 3-up,
  so long names + custom entries don't break). Exercise tiles in the same tile language. Keep top-N +
  "Show all" (§12.9) and add-inline `+ Muscle` / `+ Exercise`.
- Keep everything else from GYM-72 intact (Continue tile, faint divider, last-session pre-fill, PR chip
  `{w}kg × {r}`, one log-context call + prefetch + long cache, auto-advance, PR-beat, light+dark,
  reduced-motion, sticky in-sheet Save).
- Update `docs/frontend-spec.md` §12.2/§12.3 (picker = slide-nav + fixed height) and note the recap
  source change.

## Acceptance criteria
- [ ] Today recap shows `Set n — {w}kg × {r}` after reopen/Continue (not `Set n ✓`).
- [ ] Muscle→exercise is a horizontal push with Back; sheet height fixed (no jump) and never overlaps
      the header; muscle tiles bigger + responsive to label length / custom muscles; animation fast,
      intuitive, non-flickering; reduced-motion safe.
- [ ] `frontend-design` plugin invoked; Chalk & Iron consistency; `npm run build` green; spec updated.

## Comments

### 2026-06-05T11:00:00Z — task created
Operator-reviewed iteration on GYM-72. Frontend-design plugin mandatory; orchestrator reviews the build.

### 2026-06-05 — implemented (commit bd9b607)

**Files changed:**
- `apps/web/src/components/record/RecordPicker.tsx` — full rewrite: slide-nav track, auto-fit grid, step props
- `apps/web/src/components/record/RecordSheet.tsx` — lifted pickerStep, fixedHeight, serverSets sourcing
- `apps/web/src/components/record/SetLogger.tsx` — added serverSets prop, three-tier recap merge
- `apps/web/src/components/ui/BottomSheet.tsx` — added fixedHeight + onBackOverride props
- `apps/web/src/index.css` — picker-tile-grid utility, picker-slide-track reduced-motion rule
- `docs/frontend-spec.md` — updated §12.2/§12.3

**Layout/height decisions (frontend-design plugin, ultrathought):**

Fixed sheet height formula: `calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - var(--header-h) - 24px)`. The subtracted terms are: the Telegram/device top inset (covers notch + fullscreen Telegram controls), the AppShell header height (52px, prevents sheet overlapping the fixed header), and a 24px breathing margin. This is stricter than the default `max-height` formula (which only subtracts the inset + 24px) but is the right trade-off: the picker has fixed content that doesn't need to grow taller, and both steps must occupy the same height so there is zero jump.

Slide-nav: a 200%-wide flex row with two 50%-wide panels. The outer container is `overflow: hidden`; the track translates between `translateX(0)` (muscles) and `translateX(-50%)` (exercises) at 200ms with `--ease-out-soft` (the app's spring-ish easing). Both panels stay mounted (no remount flicker). Under `prefers-reduced-motion` the `.picker-slide-track` class removes the transition for an instant swap. `aria-hidden` on the off-screen panel, `tabIndex={-1}` on all its interactive elements to keep focus logical.

Muscle tile grid: `repeat(auto-fill, minmax(100px, 1fr))` — at 360px usable (after 16px×2 padding) yields 3 equal columns (~110px each), but long names like "Rotator Cuff" or "Upper Back" reflow to 2 columns naturally. Min tile height raised from 52px to 64px per operator request.

BackButton step-back: `BottomSheet` receives `onBackOverride?: () => boolean`; when it returns `true` the sheet's own close is suppressed. `RecordSheet` implements the override: while the picker is on the exercise step, Back steps to muscles; on the muscle step, Back closes the sheet. The current step is tracked via a `useRef` inside the override closure to avoid stale-closure bugs.

Recap fix: `SetLogger` receives `serverSets: TrainingSet[]` from `RecordSheet`, which filters `day.data.exercises` to the chosen exercise. The recap now unites three sources: session (weight/reps, priority 1), server day sets (weight/reps from the API, priority 2), and completed_set numbers (set# only, ✓ fallback, priority 3). Session beats server for the same set#. No API change required.

**Build result:** `tsc && vite build` — green, no TypeScript errors. Bundle size unchanged (no new dependencies).
