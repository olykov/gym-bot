---
schema_version: 1
id: GYM-77
title: "apps/web: name-display truncation everywhere + uniform tiles (3-col muscle/2-col exercise) + input maxLength + nav-back-empty fix"
slug: gym-77-name-display-picker-fixes
status: in_progress
priority: high
type: feature
labels: [phase-5, frontend, design, validation, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:00:00Z
finish_date: null
updated: 2026-06-05T12:00:00Z
epic: phase-5
depends_on: [GYM-74]
blocks: []
related: [GYM-75, GYM-76]
commits: []
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
