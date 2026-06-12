---
schema_version: 1
id: GYM-138
title: "Record: reps stepper adds +2 per tap; dislike weight/reps digit-switch animation"
slug: gym-138-stepper-double-step
status: in_progress
priority: high
type: bug-fix
labels: [frontend,design,record,bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: null
updated: 2026-06-12T08:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: []
tests: []
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
