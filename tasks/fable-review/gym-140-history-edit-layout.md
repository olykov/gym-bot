---
schema_version: 1
id: GYM-140
title: "History: move/delete edit UI broken — fields blown out, buttons invisible, off-style"
slug: gym-140-history-edit-layout
status: done
priority: high
type: bug-fix
labels: [frontend,design,history,bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: 2026-06-12T15:15:00Z
updated: 2026-06-12T15:15:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [c7e644c, 7b0dc10]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-140 — History: move/delete edit UI broken — fields blown out, buttons invisible, off-style

## Problem (operator, on-device review of the Fable batch)
- In History day-detail, editing is badly broken: **Move** — buttons not visible, fields blown out of
  layout, partially not even in our design system. Same for **Delete** — buttons not visible. Likely a
  Tailwind 4 migration regression in `MoveSetPanel` / `SetEditor` / `ManageMoveView` (classes that
  changed/dropped under TW4). Restore the layout + design-system styling; ensure all controls are visible
  and on-spec (docs/frontend-spec.md). ultrathink + frontend-design plugin. VERIFY visually.

## 2026-06-12 — Footer/nav-overlap residual (GYM-140 phase 2, fable-fix/sheet-footer)

Confirmed residual after fable-fix/design: headless measurements at 390×844 viewport showed the
SAVE (SetEditor) and MOVE SET (MoveSetPanel) sticky buttons landing at `{y:780, h:48}` = bottom 828,
with the BottomNav at `{y:783, h:61}` — the button overlaps the nav by 45px and is obscured/untappable.

**Root cause:** `SheetSaveButton` used `sticky bottom-0`, anchoring its lower edge to the scroll
container's bottom = viewport bottom (y:844). The BottomNav (`--nav-h: 60px`) spans y:783–844. Since
the sheet overlay (`z-sheet: 30`) is painted above the nav (`z-chrome: 20`), the button renders over
the nav visually but the native bottom chrome intercepts touch events in that zone.

**Fix applied (three files, all using `--nav-h` token, no magic px):**

1. `src/components/ui/SheetSaveButton.tsx` — changed `sticky bottom-0` to
   `sticky` + inline `style={{ bottom: "var(--nav-h)" }}`. The button now sticks
   at 60px above the scroll container's bottom (= above the nav top). Applies to
   SetEditor SAVE and MoveSetPanel MOVE SET automatically (single shared component).

2. `src/components/ui/BottomSheet.tsx` — non-fixedHeight body `paddingBottom` now
   includes `var(--nav-h)` so the scroll container has room for the sticky button to
   anchor at `bottom: var(--nav-h)`:
   - keyboard inactive: `calc(var(--nav-h) + max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + 12px)`
   - keyboard active: `calc(var(--nav-h) + keyboardPad + 12px)`

3. `src/components/ui/BottomSheet.tsx` — fixedHeight height formula now subtracts
   `var(--nav-h)` so the record-flow sheet (SetLogger) doesn't extend into the nav
   area and its flex-column controls sit above it:
   `calc(100dvh - max(...top-inset...) - var(--header-h) - var(--nav-h) - 24px)`

**Record SetLogger SAVE unaffected:** SetLogger uses fixedHeight mode, where
SheetSaveButton is inside a `shrink-0` flex item (not sticky), so the bottom of the
flex column now terminates above the nav due to the reduced sheet height. The
SheetSaveButton's `style={{ bottom: "var(--nav-h)" }}` is a no-op in non-sticky
context — it doesn't interfere.

**Green gate:** `npm ci && npm run build && npm run lint && npm run test` — all clean
(185/185 tests pass; the TS `@api-contract/schema` missing-module error was a worktree
artifact — the generated file was untracked; copying it resolved it with zero code changes).
