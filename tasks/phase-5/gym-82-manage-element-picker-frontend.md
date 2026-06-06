---
schema_version: 1
id: GYM-82
title: "apps/web: keyboard-overlap fix + no text-select on tiles + long-press manage sheet (rename/delete own, hide global) + confirm"
slug: gym-82-manage-element-picker-frontend
status: review
priority: high
type: feature
labels: [phase-5, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T08:10:00Z
start_date: 2026-06-06T17:10:00Z
finish_date: 2026-06-06T19:00:00Z
updated: 2026-06-06T19:00:00Z
epic: phase-5
depends_on: [GYM-80, GYM-81]
blocks: []
related: [GYM-74, GYM-77]
commits: [343d70b]
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

### 2026-06-06T19:00:00Z — implementation complete (343d70b)

**Keyboard-inset approach:**
Used `window.visualViewport` `resize` event to compute keyboard height as
`max(0, window.innerHeight − visualViewport.height)` while the `<BottomSheet>` is open. The sheet
body's `paddingBottom` switches from the safe-area formula to `keyboardPad + 12px` when the keyboard
is present. `AddInlineField` additionally calls `scrollIntoView({ behavior:'smooth', block:'center' })`
on focus so the input and its submit button always land above the keyboard. No Telegram SDK interaction
needed — `visualViewport` is reliable in all target WebViews. Resets to 0 on sheet close.

**Tap vs long-press:**
`useTilePressHandlers` hook in `RecordPicker.tsx` (~40 lines): `pointerdown` → 480ms timer; cancel
on `pointermove` > 6px or on `pointerup` before timer fires (= normal tap). Timer fires → long-press:
`hapticImpact('medium')` + open manage sheet. `onContextMenu` prevents the iOS native popup after a
long-press. No library; fully compatible with the existing `.press-95` / 0.98-scale micro-interaction.
Reduced-motion: haptic stays, `BottomSheet` slide already gated by `prefers-reduced-motion`.

**Manage-sheet design + ownership gating:**
`ManageSheet.tsx` reuses `<BottomSheet>` (auto-height). Bebas Neue item-name headline + Sora kind
label. Four internal views (state machine in the component): `actions` → `rename` / `confirm-delete`
/ `offer-hide`. All Chalk & Iron tokens only.
- Own items: Rename (AddInlineField pre-filled, same maxLength) + Delete (confirm step, --accent fill
  button). 409 on rename → "That name is already in use."; 422 → server message.
- Delete 409 (has history) → offer-hide view: "has logged history and can't be deleted. Hide it
  from your picker instead?" with Cancel + Hide.
- Global items: "Hide from my list" only → PUT /muscles/{id}/hidden or PUT /exercises/{id}/hidden.

**409-history → hide flow:**
On `deleteExercise`/`deleteMuscle` returning a 409, the `onError` callback in `ManageSheet`
switches the view from `confirm-delete` to `offer-hide` (does NOT close or show a raw error). The
Hide button then calls the appropriate hide hook. This covers the spec requirement exactly.

**Hooks + invalidation (useRecord.ts):**
Added: `useRenameMuscle`, `useRenameExercise`, `useDeleteMuscle`, `useDeleteExercise`,
`useHideMuscle`, `useHideExercise`. All invalidate `["muscles"]`, `["analytics","top-muscles"]`,
`["analytics","top-exercises"]` on success. `useRenameExercise` additionally invalidates
`["analytics","exercise-progress"]` and `["analytics","top-exercises",muscleName]` so progress
charts keyed by the exercise name pick up the new name.

**Exercise id lookup:**
`useTopExercises` returns only `{name, frequency}` (no `id`/`is_mine`). Added `useExercises` import
in `RecordPicker`; when a muscle is selected, derives its numeric id from `muscleByName` (from
`useMuscles()`), then uses `useExercises(selectedMuscleId)` to build `exerciseByName` Map for
id/is_mine lookup. The query is already cached (5-min staleTime) and prefetched via the existing
muscle-pick flow; no extra network round-trip on the happy path.

**Build result:** `tsc && vite build` green (0 type errors, 0 warnings beyond the pre-existing chunk
size note). 726 modules, 1.4 MB bundle, 462 KB gzip.

**Needs live-device pass:**
1. Keyboard inset: verify on an actual Telegram iOS/Android open — ensure the add-input field is
   fully above the keyboard and the sheet does not clip on a 360px device.
2. Long-press timer feel: 480ms feels right in emulation; may need ±40ms tuning on real hardware
   (Android tends to be more sensitive to the delay than iOS).
3. Manage-sheet for a global exercise: confirm that the `useExercises(selectedMuscleId)` call
   correctly returns `is_mine: false` for catalog items (depends on GYM-81 API implementation).
4. Dark-mode: the manage-sheet action rows use `--secondary-bg`/`--text`/`--accent` — verify
   contrast of the destructive "Delete" row (`--accent` text on `--secondary-bg`) in Telegram dark.
5. Tile text-select suppression: verify `-webkit-touch-callout: none` fully suppresses the iOS
   "Copy / Look Up / Share" popup that appears on a 500ms press.
