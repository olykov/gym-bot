---
schema_version: 1
id: GYM-151
title: "Set steppers: WEIGHT and REPS numbers centered on different axes (kg unit shifts WEIGHT)"
slug: gym-151-stepper-number-centering
status: todo
priority: high
type: bug-fix
labels: [frontend, design, record, sheet, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T06:45:00Z
updated: 2026-06-13T06:45:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-143]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-151 — Stepper numbers not centered consistently

## Problem (operator, on-device)
The WEIGHT and REPS stepper fields are the same width, but the numbers sit on different
horizontal axes — looks painful. Cause (`Stepper.tsx`): the field is
`flex justify-center [input w-full text-center][span unit]`. WEIGHT has a `kg` unit span
that consumes right-side space, so the input (and its centered text) is centered in
`width − kg` → shifted LEFT of the true center. REPS has no unit → centered in the full
width → true center. The two numbers therefore don't line up.

## Plan (frontend-design + plugin)
The numeric value must be optically centered in the field REGARDLESS of the unit, so
WEIGHT and REPS share the same vertical axis. Likely: position the unit as an affix that
does not affect the input's centering (absolute right, or a symmetric reserved gutter on
both sides). Keep ≥44px targets, tabular-nums, no jitter. Obey docs/frontend-spec.md.
Verify headless dark + realistic insets: WEIGHT "50" and REPS "10" centers align.

## Comments

### 2026-06-13T06:45:00Z — filed + approved for this iteration
