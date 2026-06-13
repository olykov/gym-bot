---
schema_version: 1
id: GYM-151
title: "Set steppers: WEIGHT and REPS numbers centered on different axes (kg unit shifts WEIGHT)"
slug: gym-151-stepper-number-centering
status: done
priority: high
type: bug-fix
labels: [frontend, design, record, sheet, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T06:45:00Z
updated: 2026-06-13T11:00:00Z
start_date: 2026-06-13T07:00:00Z
finish_date: 2026-06-13T11:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-143]
commits: [aa60662]
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

### 2026-06-13T11:00:00Z — closed (aa60662)
Fixed in `apps/web/src/components/ui/Stepper.tsx`: field container changed from
`flex justify-center gap-1` (unit in flow) to `relative` with unit `absolute right-3
inset-y-0`. Input is `w-full h-full text-center` and centers over the full field width
regardless of unit presence. Verified headless Playwright dark theme: WEIGHT centerX =
196.50px, REPS centerX = 196.50px, delta = 0.00px (≤ 1px threshold met). Build ✅
lint ✅ 198 tests ✅.
