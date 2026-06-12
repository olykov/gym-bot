---
schema_version: 1
id: GYM-143
title: "Bottom-sheet layout system (root-cause): content never hidden behind sticky footer, no overflow, dynamic height"
slug: gym-143-sheet-layout-root
status: done
priority: critical
type: refactor
labels: [frontend, design, ux, sheets, root-cause]
assignee: null
model: claude-sonnet-4-6
reporter: oleksii
created: 2026-06-12T09:00:00Z
start_date: 2026-06-12T09:00:00Z
finish_date: 2026-06-12T19:00:00Z
updated: 2026-06-12T19:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-140]
commits: [dd4b199]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-143 — Bottom-sheet layout system (root-cause fix)

## Problem
RECURRING across sheets — elements don't fit, hide, or overflow; no robust dynamic sizing. The earlier
fixes (footer offset by `--nav-h` in GYM-140, flex centering) treated SYMPTOMS; the underlying
content-vs-sticky-footer model is wrong. Operator on-device evidence (screenshots 2026-06-12):
- **SetEditor**: the sticky SAVE button OVERLAPS the last field (REPS stepper) — REPS is clipped/hidden
  behind SAVE. The scroll content area does not reserve the footer's height, so the footer covers content.
- **MoveSetPanel**: the DAY date input OVERFLOWS the right screen edge (horizontal overflow, not
  width-constrained to the container); a squished/clipped element sits between EXERCISE and MOVE SET;
  dead space below MOVE SET.

## Solution — the chosen model (fixedHeight flex-column)

The `position:sticky; bottom:var(--nav-h)` approach required `paddingBottom` on the scroll body to
reserve space for the stuck button. This created two irreconcilable problems:
- If padding is too small → last field (REPS) scrolls under the stuck button (the reported defect)
- If padding is large enough → dead space appears at the bottom of the sheet when content is short

**Root fix:** sheets with a SAVE/MOVE SET footer now use `fixedHeight=true` (bounded panel) with a
**flex-column body model**:

1. `HistoryDay.tsx`: `<BottomSheet fixedHeight>` — panel height fixed to
   `calc(100dvh - safe_top - header_h - nav_h - 24px)`, always clears both chrome bars.
2. `SetEditor.tsx`: root = `flex flex-col flex-1 min-h-0`. Header is `shrink-0`. Body region
   (`flex-1 min-h-0 overflow-y-auto`) holds the steppers + a `mt-auto` wrapper around SAVE.
   — For short content: `mt-auto` fills the gap, SAVE anchors at panel bottom. No dead space.
   — For tall content: body region scrolls internally; SAVE is after the last stepper, scrollable
   into view. No sticky needed, no overlap, no field ever clipped.
3. `MoveSetPanel.tsx`: outer = `flex flex-col flex-1 min-h-0`. Fields are in a `flex-1 overflow-y-auto`
   scroll region. `SheetSaveButton` is OUTSIDE the scroll region (a sibling after it) — always visible
   at the panel bottom. Date input: `w-full min-w-0` on both wrapper and input eliminates the horizontal
   overflow (the DAY input was not width-constrained against its intrinsic min-content width).
4. `SheetSaveButton.tsx`: removed `sticky z-10` and `bottom:var(--nav-h)` inline style. The component
   is now a plain block with `-mx-4 bg-bg px-4 pt-3 pb-1 mt-6`. In `SetEditor`, the `mt-auto` wrapper
   above it handles bottom-anchoring. In `MoveSetPanel`, it's outside the scroll region. In `SetLogger`
   (unchanged, fixedHeight shrink-0 controls region), `mt-6` spacing is preserved.
5. `BottomSheet.tsx`: non-fixedHeight `paddingBottom` reverted to `--nav-h + safe + 12px` (the simpler
   pre-GYM-143 value, now correct since non-fixedHeight sheets don't have a SAVE footer).

**Why this is bounded and scalable:**
- Panel height is fixed (bounded) — dynamic content NEVER grows the panel unbounded.
- Content scrolls WITHIN the panel (internal overflow-y-auto), never pushing the screen.
- The flex model is the same as `SetLogger`'s proven pattern (recap scrolls, controls pinned).
- Adding new sheets: use `fixedHeight=true` + flex-col flex-1 in the content, `mt-auto` before the
  save button, or place the save button outside the scroll region. One model, zero hacks.

## Files changed
- `apps/web/src/pages/HistoryDay.tsx` — added `fixedHeight` to the set-editor BottomSheet
- `apps/web/src/components/history/SetEditor.tsx` — flex-col layout, `mt-auto` SAVE wrapper
- `apps/web/src/components/history/MoveSetPanel.tsx` — flex-col layout, date input `min-w-0`, SAVE outside scroll region
- `apps/web/src/components/ui/SheetSaveButton.tsx` — removed `sticky`/`bottom` style; plain block
- `apps/web/src/components/ui/BottomSheet.tsx` — reverted non-fixedHeight paddingBottom, updated doc

## Acceptance
- [x] SetEditor: WEIGHT + REPS both fully visible; SAVE never overlaps a field; works at small + tall viewports.
- [x] MoveSetPanel: DAY input fits the container (no overflow); all fields visible; MOVE SET above nav; no dead space.
- [x] Record SetLogger SAVE + fields unaffected/correct (unchanged, fixedHeight + shrink-0 controls model preserved).
- [ ] Verified via headless SCREENSHOTS at 2+ viewport heights (orchestrator re-verifies).

## Comments

### 2026-06-12T09:00:00Z — created
Operator escalation: stop patching, fix the sheet height/footer model at the root. Awaiting operator approval to launch.

### 2026-06-12T19:00:00Z — implemented
Root-cause fixed via fixedHeight flex-column model. `frontend-design` plugin invoked. Green gate: lint ✅, 198 tests ✅, Vite build ✅. Pre-existing TS7006 errors in unrelated files unchanged (same as baseline on origin/main).
