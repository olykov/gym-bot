---
schema_version: 1
id: GYM-122
title: "Stepper: hold-to-repeat on ± with acceleration"
slug: gym-122-stepper-hold-to-repeat
status: review
priority: medium
type: feature
labels: [frontend, ux, record]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:30:00Z
start_date: 2026-06-12T15:05:00Z
finish_date: null
updated: 2026-06-12T15:05:00Z
epic: ux-polish
depends_on: []
blocks: []
related: []
commits: []
tests: []
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-122 — Stepper hold-to-repeat

## Problem
Review doc 01 §4. Going 100kg → 60kg is 16 taps on the − button. Spec §11.4 lists
hold-to-repeat as the sanctioned nice-to-have.

## Solution
- Pointer-hold on ±: after 400ms start repeating at 250ms, accelerate to 80ms after ~8 steps.
  Cancel on pointerup/leave/cancel; `setPointerCapture`.
- Haptic: light selection tick every step would spam — fire on first repeat and then every
  5th step only.
- Reduced-motion: no animated ramp (per spec) — repeat is allowed, value just updates.
- While here: extract the shared weight/reps constants if GYM-126 hasn't landed
  (`WEIGHT_STEP = 2.5` lives in 3 files) — coordinate.
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin.

## Acceptance criteria
- [ ] Hold ± repeats with acceleration; tap still steps once; min-clamp respected. *(timing engine — initial delay, interval, acceleration, cancel, min-clamp stop — covered by 9 fake-timer unit tests; the touch gesture itself needs a real-device check)*
- [x] Works in SetLogger, SetEditor, AddSetInline (shared `<Stepper>` — one change). *(code-verifiable: the hold lives in the shared `StepButton`; all three call sites render the same `<Stepper>`)*

## Comments

### 2026-06-12T09:30:00Z — task created

### 2026-06-12T15:05:00Z — implemented (agent wave 4a)

- Files: `apps/web/src/components/ui/useHoldRepeat.ts` (new: pure `createHoldRepeat` engine + `useHoldRepeat` pointer binding), `useHoldRepeat.test.ts` (new, 9 tests), `Stepper.tsx` (StepButton wiring, `stepBy` returns clamped-flag), `Stepper.test.ts` (mock `@/telegram/webapp` — Stepper now imports the haptic helper and the raw SDK touches `window` at import time in the node test env), `src/validation.ts` + `SetLogger.tsx` / `SetEditor.tsx` / `AddSetInline.tsx` (`WEIGHT_STEP = 2.5` consolidation).
- Choices:
  - Engine is pure/callback-based (no React/DOM) so vitest fake timers verify the contract: first repeat at 400ms, then 250ms, accelerating to 80ms after 8 repeats; `onTick` returning false (min clamp) stops the run.
  - Initial press steps once on pointerdown; the trailing synthetic click is suppressed (so a tap never double-steps) while keyboard Enter/Space still steps via click. Cancel on pointerup/pointerleave/pointercancel; guarded `setPointerCapture` (SetRow idiom); `touch-none` on the ± buttons so a hold repeats instead of becoming a sheet scroll.
  - Min-clamp: `stepBy` checks before mutating and reports false → repeats self-stop at min even though the disabled button stops emitting pointer events mid-hold; − disabled-state logic unchanged.
  - Haptic: light impact on repeat tick 1, then every 5th tick, only when a step actually happened; no haptic on the initial press (unchanged tap feel).
  - Reduced-motion: nothing to gate — repeating is input, and no ramp visuals were added.
  - WEIGHT_STEP: trivial, done here (single constant in `src/validation.ts`, used by all three steppers); the broader dedup remains with GYM-126.
- Verification: bench `tsc --noEmit`, `eslint --max-warnings 0`, `vitest run` (81 tests, 9 new), `vite build` — all pass. Real-device hold feel not yet verified.
- No file overlap with GYM-120 (separate commit-safe).
- Suggested commit: `Add stepper hold-to-repeat with acceleration and haptics`
