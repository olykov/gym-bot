---
schema_version: 1
id: GYM-98
title: "apps/web: move pending only on tapped muscle + sheet white-strip dim fix + app-wide no text-select"
slug: gym-98-manage-move-polish
status: done
priority: high
type: bug-fix
labels: [phase-5, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T12:00:00Z
start_date: 2026-06-08T12:00:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: phase-5
depends_on: [GYM-90]
related: [GYM-82]
commits: [4f0b9fc]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-98 — Manage/move polish (3 live issues)

## Problem (operator, live)
1. During a move, the "Moving..." pending state shows on the WHOLE muscle list, not just the muscle the
   user tapped. Should be only on the tapped target. (Root: ManageSheet uses one global
   `isPendingMutation` boolean.)
2. On long-press the sheet/scrim darkens nicely, BUT there is a white mini-shelf at the very TOP of the
   sheet (the grab-handle / `pt-3 bg-bg` strip) that does not darken — looks broken.
3. Outside tiles/buttons, text can still be selected by long-press. Disable text selection app-wide for a
   native app feel (keep inputs/textareas + any intentionally selectable content selectable).

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only, no new lib)
- #1: replace the global pending gate in the move view with a per-target pending — track the tapped
  `muscle_id` (e.g. `movingMuscleId`), show the spinner/"Moving..." ONLY on that row; other rows stay
  normal and disabled-but-not-spinning. Keep error handling (409 stays in view, etc.).
- #2: reproduce and fix the white strip at the top of the BottomSheet during the long-press dim — the
  top handle/`pt-3` area must be visually consistent with the rest of the sheet under the dim/scrim (no
  unscrimmed white sliver). Diagnose via the plugin; fix with tokens (likely the scrim layering / the
  panel top bg). Don't regress the fixed-height / header-clearance from GYM-74.
- #3: apply `user-select:none` (+ `-webkit-user-select`, `-webkit-touch-callout:none`) at the app
  root/body so long-press never selects text anywhere; explicitly RE-ENABLE selection on inputs,
  textareas, and any content meant to be selectable (`user-select:text`). Verify inputs still work.

## Acceptance criteria
- [ ] Move spinner shows only on the tapped muscle; no white strip atop the sheet under the dim; long-press
      selects no text anywhere (inputs still selectable/editable); plugin invoked; build green.

## Comments

### 2026-06-08T12:00:00Z — task created
Live polish on GYM-90 + app-wide selection. Frontend-design plugin mandatory.

### 2026-06-08 — implemented (4f0b9fc)

**Issue 1 — per-row move pending:**
Added `movingMuscleId: number | null` state to ManageSheet. `submitMove()` sets it to the
tapped `targetMuscleId` before calling `moveExercise.mutate()`, then resets to null in
`onError` (success calls `handleClose()` which also resets). The move view renders
`isThisRowMoving = movingMuscleId === m.id` per row: only that row shows "Moving…"; other
rows stay `disabled` (opacity-40) but show their normal name. `handleClose()` also resets
`movingMuscleId` for the 409-stays-in-view path.

**Issue 2 — sheet top white strip under dim:**
Root cause: ManageSheet's BottomSheet is rendered inside RecordSheet's BottomSheet panel.
Both use `fixed inset-0 z-30`. Because RecordSheet's panel has a CSS animation (sheet-rise,
forwards fill) with a transform, it establishes a stacking context. ManageSheet's fixed
z-30 overlay is stacked WITHIN that context, so the RecordSheet panel's top area (grab
handle / pt-3 / bg-bg) sits outside ManageSheet's paint reach — appearing as an
unscrimmed white sliver above ManageSheet's scrim.
Fix: added optional `zIndex` prop (default 30) to BottomSheet; ManageSheet passes
`zIndex={40}`. At z-40 the ManageSheet overlay escapes the RecordSheet stacking context
and covers the entire viewport uniformly. No regression to GYM-74 fixed-height /
header-clearance (RecordSheet still uses `fixedHeight=true`, unchanged).

**Issue 3 — app-wide no text selection:**
Added `-webkit-user-select: none; user-select: none; -webkit-touch-callout: none` to
`body` in index.css (inside `@layer base`). Followed immediately by an explicit re-enable
rule for `input, textarea, [contenteditable]` restoring `-webkit-user-select: text;
user-select: text; -webkit-touch-callout: default`. The existing `.tile-no-select` class
is now redundant but kept for documentation clarity. Inputs, the add-name field, and
weight/reps steppers are unaffected.

**Build:** `tsc && vite build` green (0 errors). Pre-existing chunk-size warning
(1,425 kB bundle) unchanged.

**Needs live-device pass:** Issue 2 fix (z-index elevation) should be verified on iOS
Telegram — confirm no unscrimmed white strip at the RecordSheet panel top when ManageSheet
opens. Issue 3 — verify add-name input focus, caret, and selection on iOS touch.
