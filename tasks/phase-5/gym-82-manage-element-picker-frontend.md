---
schema_version: 1
id: GYM-82
title: "apps/web: keyboard-overlap fix + no text-select on tiles + long-press manage sheet (rename/delete own, hide global) + confirm"
slug: gym-82-manage-element-picker-frontend
status: in_progress
priority: high
type: feature
labels: [phase-5, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T17:10:00Z
finish_date: null
updated: 2026-06-06T08:10:00Z
epic: phase-5
depends_on: [GYM-80, GYM-81]
blocks: []
related: [GYM-74, GYM-77]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-82 — Keyboard fix + long-press manage element

## Problem (operator feedback)
1. **Keyboard overlaps the add-name input.** Tapping "+ Muscle" / "+ Exercise" raises the Telegram/iOS
   keyboard which covers the input field. Fix within the design system.
2. **Long-press selects the tile's text.** Disable that. AND add a NEW capability: long-press a
   muscle/exercise tile → a small in-design sheet to **rename** or **delete** the element, with
   **confirmation** on delete. All in the app's Chalk & Iron language.

## Plan (frontend-design-engineer — MANDATORY: invoke `/frontend-design:frontend-design` and ultrathink; obey docs/frontend-spec.md; Chalk & Iron, all our tokens/components/canons & prohibitions; no new lib)

### #1 — keyboard no longer covers the add-input
- When the add-name field is focused, keep it visible above the keyboard. Use the Telegram WebApp
  viewport (`viewportChanged` / `@twa-dev/sdk`) and/or `window.visualViewport` resize to track keyboard
  height; pad/scroll the sheet so the focused input sits above the keyboard (e.g. `scrollIntoView` on
  focus + a keyboard-inset bottom pad on the sheet scroll container). The designer picks the cleanest
  in-shell approach (the BottomSheet must still respect the fixed header / safe-area from GYM-74). Verify
  the input + its submit affordance are fully visible while typing on a real device.

### #2 — no text selection + long-press manage sheet
- Add `user-select: none` (+ `-webkit-user-select: none`, `-webkit-touch-callout: none`) to muscle/
  exercise tiles so long-press no longer selects text.
- **Long-press** (~450–550ms, with `hapticImpact`) on a muscle OR exercise tile opens a **manage sheet**
  (reuse BottomSheet / our action-row language). Tap still = normal select; distinguish tap vs long-press
  (pointerdown timer, cancel on move/scroll/early-up). Respect reduced-motion.
- **Ownership-gated actions** (use the `is_mine` field from GYM-80/81):
  - **Own custom item** (`is_mine: true`): **Rename** + **Delete**.
    - Rename → inline edit (reuse AddInlineField pattern + the maxLength constants from validation.ts,
      30/40, trim) → `PATCH /muscles/{id}` or `PATCH /exercises/{id}`. On 409 (dup name) show a graceful
      inline message; on 422 show the server message.
    - Delete → a **confirmation** step (in-design, destructive accent) → `DELETE /muscles/{id}` /
      `DELETE /exercises/{id}`. On **409 (has history)** surface "this has logged history — hide it
      instead?" and offer the Hide action rather than failing silently.
  - **Global catalog item** (`is_mine: false`): **Hide** only (remove from my picker) → the existing
    `PUT /muscles/{id}/hidden` (and the exercise hide endpoint). No rename/delete on shared items.
- On success: optimistic/invalidate the muscles & exercises queries (and top-muscles/top-exercises) so the
  tile updates/disappears; a renamed exercise's downstream views refresh. Keep the picker's slide-nav,
  fixed height, Continue tile, etc. intact.
- Update `docs/frontend-spec.md` (§12.2 manage-element interaction + a note on the keyboard-inset handling).

## Acceptance criteria
- [ ] Add-name input stays visible above the keyboard. Tiles no longer select text on long-press.
- [ ] Long-press opens an in-design manage sheet: own items → Rename + Delete (with confirm; 409-history →
      offer Hide); global items → Hide only. Wired to the GYM-80/81 endpoints; lists refresh.
- [ ] `frontend-design` plugin invoked; Chalk & Iron + all canons respected; `npm run build` green; spec updated.

## Comments

### 2026-06-06T08:10:00Z — task created
Depends on GYM-80 (contract) + GYM-81 (rename/delete-guard endpoints + is_mine). Frontend-design plugin
mandatory — the operator wants this strictly in the app's style, all our elements/prohibitions/canons.
