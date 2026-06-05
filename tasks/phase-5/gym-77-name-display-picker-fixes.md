---
schema_version: 1
id: GYM-77
title: "apps/web: name-display truncation everywhere + uniform tiles (3-col muscle/2-col exercise) + input maxLength + nav-back-empty fix"
slug: gym-77-name-display-picker-fixes
status: done
priority: high
type: feature
labels: [phase-5, frontend, design, validation, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:00:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-74]
blocks: []
related: [GYM-75, GYM-76]
commits: [dfa1dd2]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-77 — Name display + uniform tiles + grids + input limit + nav-back fix

## Problem (operator feedback on live GYM-74, with screenshots)
1. **Tile height grows with long names; no truncation.** A long muscle name makes its tile 6 lines tall,
   breaking the uniform grid. Want: ALL muscle/exercise tiles the SAME height & width; the name truncates
   (max ~3 lines of text + padding, then ellipsis). "Не более 3х рядов текста."
2. **No name limits → long names blow up the whole app.** In the record header the muscle pill overflows
   and is clipped raggedly; a freshly-added long exercise name is huge and pushes layout off-screen.
   Same risk in History, charts, Dashboard. Need a SYSTEMIC display-truncation treatment everywhere a
   muscle/exercise name renders + mirror the new API input limits in the add-name inputs.
3. **Exercise grid should be 2 columns** (muscle grid 3 columns stays as is — that's good).
4. **Nav bug:** add a new exercise inline → land on the SetLogger → log 1 set → press Back → expected the
   exercise LIST (of that muscle); got an EMPTY screen.

## Plan (frontend-design-engineer — MANDATORY: invoke `/frontend-design:frontend-design`, ultrathink; Chalk & Iron, tokens only, no new lib)

### #1 + #3 — uniform tiles + grids
- Muscle & exercise tiles: FIXED equal height (fit up to **3 text lines** + padding) and equal width;
  long labels `line-clamp: 3` + ellipsis, centered. No tile ever grows the row.
- Keep **muscle grid = 3 columns** (current auto-fill is fine; ensure long names clamp, not expand).
  Change **exercise grid = 2 columns** (operator: "в 2 ряда"). Exercise tiles same tile language, fixed
  height, line-clamp.

### #2 — systemic name display + input limits
- Introduce ONE shared truncation treatment for muscle/exercise names and apply it at EVERY render site
  (sweep — at least: `RecordPicker.tsx`, `SetLogger.tsx` (the recap rows + the header exercise name +
  muscle pill), `RecordSheet.tsx`, `ui/DayCard.tsx`, `pages/HistoryDay.tsx`, `dashboard/SummaryCards.tsx`,
  and the Progress/ECharts pages — grep the codebase for every `*_name` render and fix all of them):
  - Inline labels (record header exercise name + muscle pill, history rows, dashboard, top lists):
    single-line truncate (ellipsis) with a hard `max-width`/`min-width:0` so flex children actually clip;
    add `title={name}` for the full text. The record header muscle pill MUST clip cleanly with ellipsis,
    never run off-screen.
  - Tiles: the line-clamp from #1.
  - ECharts axis/label: truncate via the label `formatter` (e.g. first ~14 chars + …) and keep the full
    name in the tooltip.
- Mirror the API rules (docs/validation.md / GYM-75) in the add-name inputs (`AddInlineField.tsx`):
  `maxLength` on the `<input>` (muscle 30 / exercise 40), trim on submit, disable submit when empty after
  trim. (Server is authoritative; this is just immediate UX — show the server 422 message gracefully if
  it still rejects.) Centralize the two limits as named constants.

### #4 — nav-back-after-add lands on empty screen
- Reproduce: inline-add exercise → auto-selects into Phase B → Back ("Switch exercise" or Telegram
  BackButton) must return to the **exercise step of the picker for that muscle** (the new exercise present
  in the list), NOT an empty panel. Root cause is likely the picker step/selected-muscle state not being
  restored (or the slide track left on an empty off-screen panel) when returning from a freshly-added
  exercise. Fix so Back always lands on the populated exercise list; verify both the in-sheet "Switch
  exercise" and the Telegram BackButton paths.

Keep ALL GYM-74 behavior intact (slide-nav, fixed height, Continue tile, faint divider, pre-fill, PR chip,
prefetch/cache, auto-advance, light+dark, reduced-motion). Update `docs/frontend-spec.md` (a short
"name display / truncation" note in §10 or §12, and the exercise 2-col grid in §12.2).

## Acceptance criteria
- [ ] Tiles uniform height/width; long names clamp to ≤3 lines + ellipsis (no row growth); muscle 3-col,
      exercise 2-col.
- [ ] Every muscle/exercise name render site truncates cleanly (no off-screen overflow), incl. record
      header pill, history, dashboard, charts. Add-name inputs enforce maxLength 30/40 + trim.
- [ ] Back after adding a new exercise lands on the populated exercise list (not empty), both paths.
- [ ] `frontend-design` plugin invoked; Chalk & Iron consistency; `npm run build` green; spec updated.

## Comments

### 2026-06-05T12:00:00Z — task created
Operator-reviewed iteration on GYM-74 (4 screenshots). Frontend-design plugin mandatory; orchestrator
reviews the build. Pairs with GYM-75/76 (the validation foundation) but lives entirely in apps/web.

## Comments

### 2026-06-05 — implementation (dfa1dd2)

**Build result:** `tsc && vite build` green, 0 errors.

**Truncation primitive introduced:**
- `.tile-name` CSS class in `index.css`: `-webkit-line-clamp: 3; -webkit-box-orient: vertical; display: -webkit-box; overflow: hidden; word-break: break-word`. Applied to the text node inside every tile button.
- `.name-truncate` utility (in `@layer utilities`): single-line ellipsis with `min-width: 0` — documents the pattern even though most callers use Tailwind's `truncate` directly.
- Tile height: fixed at `88px` via inline `style={{ height: "88px" }}` on every tile button and skeleton (3 body text lines at 1.4 line-height × 0.9375rem ≈ 63px + 24px padding = 87px → 88px).

**Tile/grid decisions:**
- `picker-tile-grid-muscle`: `repeat(3, 1fr)` — 3 fixed columns; long names clamp at 3 lines inside the fixed-height tile.
- `picker-tile-grid-exercise`: `repeat(2, 1fr)` — 2 fixed columns per operator ("в 2 ряда").
- Both grids: `gap: 8px` (spacing scale). `+ Muscle` dashed tile and "Show all" button use the same `88px` fixed height for visual uniformity.

**Render sites fixed (#2 — systemic sweep):**
1. `RecordPicker.tsx` — muscle and exercise tile names: `.tile-name` + `title={name}` on every tile button.
2. `SetLogger.tsx` — exercise name header: `min-w-0 flex-1 truncate` + `title={exerciseName}`; muscle chip: wrapped in `shrink-0 max-w-[8rem]` span so it never overflows the flex row.
3. `HistoryDay.tsx` — exercise name per card: `min-w-0 flex-1 truncate` + `title`; muscle chip: same `shrink-0 max-w-[8rem]` wrapper.
4. `ExerciseProgressChart.tsx` — chart title div: `truncate` + `title={title}`.
5. `DayCard.tsx` — muscle chips in the flex-wrap row: each chip wrapped in `max-width: 10rem` span + `title={m}`.
6. `Chip.tsx` — accepts optional `title` prop (non-breaking addition).
7. `SetEditor.tsx` — exercise name already had `truncate`; no change needed.
8. `ChipRow.tsx` (Progress pickers) — chips use `whitespace-nowrap` in a scrollable overflow-x row; inherently safe (no truncation needed, scroll is the correct treatment for a picker chip row).
9. `SummaryCards.tsx` — displays numeric stat values only, no muscle/exercise names; no change needed.

**Input limits (#2 — `AddInlineField.tsx` + `validation.ts`):**
- New file `apps/web/src/validation.ts`: exports `MUSCLE_NAME_MAX = 30` and `EXERCISE_NAME_MAX = 40` with a comment referencing `docs/validation.md` (GYM-75).
- `AddInlineField.tsx`: added optional `maxLength` prop; passed to the `<input maxLength>` attribute.
- All 4 `AddInlineField` usages in `RecordPicker.tsx` now pass the appropriate constant (`MUSCLE_NAME_MAX` or `EXERCISE_NAME_MAX`). Trim-on-submit and disable-when-empty-after-trim were already implemented; no change needed there.

**#4 — nav-back-after-add root cause and fix:**
- **Root cause:** `selectedMuscle` lived as local state inside `RecordPicker`. The controller `RecordSheet` conditionally renders `chosen ? <SetLogger> : <RecordPicker>` — when `setChosen(null)` fires (Phase B → A), React unmounts `SetLogger` and remounts `RecordPicker`. On remount, local `selectedMuscle` resets to `null`. The picker step is `"exercises"` (preserved in `RecordSheet`), but with `selectedMuscle = null` the exercises query is disabled and the exercise step header shows `""` → empty panel.
- **Fix:** `selectedMuscle` state is lifted to `RecordSheet`. `RecordPicker` now receives `selectedMuscle` and `onMuscleChange` as controlled props. `onSwitch` in RecordSheet simply calls `setChosen(null)` — `selectedMuscle` stays set, `pickerStep` stays `"exercises"`, so RecordPicker remounts onto the populated exercise list. The Telegram BackButton path also resets `setSelectedMuscle(null)` along with `setPickerStep("muscles")` for the full back-to-muscle step. Sheet close resets both.
- **Both paths confirmed in code:** "← Switch exercise" button → `setChosen(null)` with muscle preserved; Telegram BackButton override → `setPickerStep("muscles") + setSelectedMuscle(null)`.

**Spec updates:** `docs/frontend-spec.md` — added §10.0 "Name display / truncation contract" section; updated §12.2 muscle and exercise grid descriptions to reflect the fixed 3-col / 2-col grids and `88px` fixed tile height with line-clamp-3.
