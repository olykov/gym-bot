---
schema_version: 1
id: GYM-138
title: "Record: reps stepper adds +2 per tap; dislike weight/reps digit-switch animation"
slug: gym-138-stepper-double-step
status: done
priority: high
type: bug-fix
labels: [frontend,design,record,bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: 2026-06-12T11:00:00Z
updated: 2026-06-12T11:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [c7e644c]
tests: [apps/web/src/components/ui/useHoldRepeat.test.ts]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-138 — Record: reps stepper adds +2 per tap; dislike weight/reps digit-switch animation

## Problem (operator, on-device review of the Fable batch)
- A single tap on reps `+` increments by **2** (should be 1). Stepper uses `useHoldRepeat`
  (pointerdown steps tick 0 + suppresses the synthetic click; `onClick={hold.onClick}` IS wired in
  StepButton) — so suspect a real-device double-fire the suppression misses, OR a step config. Reproduce
  on touch; harden so a tap steps EXACTLY once (weight too).
- The weight/reps **digit-switch animation** (number roll, GYM-131 choreography) is disliked — remove or
  greatly simplify it. ultrathink + frontend-design plugin.

## Root cause and fix (SHA: c7e644c, branch: fable-fix/design)

### Double-step bug
`useHoldRepeat` used `suppressClickRef` (boolean) + `setTimeout(0)` to suppress the synthetic click
that touch devices emit after `pointerdown`. Race condition: on real Android WebViews (Telegram in-app
browser), `setTimeout(0)` resolved **before** the synthetic click fired, clearing the flag early —
the click stepped a second time.

Fix: **timestamp-based guard** (`POINTER_CLICK_GUARD_MS = 300ms`). On `pointerdown`, record
`Date.now()`. On `onClick`, if the click arrives within 300 ms of the last pointerdown, it is the
touch-generated synthetic click and is suppressed. Genuine keyboard activations happen well after
any prior pointer interaction and pass through normally.

Architecture: extracted the handler logic into `createHoldHandlers(step, now)` — a pure factory with
no React dependencies and an injectable clock so the guard is unit-testable without jsdom/RTL.
`useHoldRepeat` is now a thin React wrapper over it.

### Digit animation removal
`RollingNumber` (the SET N heading digit roll in `SetHeadingRow`) replaced with a plain
`<span className="tabular">{nextSet}</span>`. Per operator request — the animation is disliked.

### Tests added (5 new in useHoldRepeat.test.ts, total 190)
- `pointerdown → pointerup → click` = exactly one step (the core regression)
- Late click (> guard window) = two steps (genuine keyboard not blocked)
- Standalone click (no prior pointerdown) = one step (keyboard activation)
- `pointercancel` clears the guard (no state leak)
- Second tap after guard expires = one step per tap (no inter-tap leakage)
