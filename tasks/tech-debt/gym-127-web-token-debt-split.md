---
schema_version: 1
id: GYM-127
title: "apps/web token debt: --tile-h, chip max-width, z-scale, dead --stat-size + split RecordPicker (<500 lines)"
slug: gym-127-web-token-debt-split
status: review
priority: medium
type: refactor
labels: [frontend, refactor, tokens, design-system]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:55:00Z
start_date: 2026-06-12T15:30:00Z
finish_date: null
updated: 2026-06-12T15:30:00Z
epic: tech-debt
depends_on: [GYM-124]
blocks: []
related: [GYM-126]
commits: []
tests: []
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-127 — Token debt + RecordPicker split

## Problem
Review doc 02 §4: magic values violating the repo's own tokens-only rule, and
`RecordPicker.tsx` at 1139 lines vs the <500 limit.

## Solution
1. `--tile-h: 88px` in tokens.css (the index.css comment references it but it doesn't
   exist); replace all 8 inline `style={{height:"88px"}}` with a `.tile-h` utility /
   Tailwind token.
2. Chip caps: `--chip-max` token replacing the 4 inline `maxWidth: "8rem"/"10rem"`.
3. z-index scale: `--z-chrome` / `--z-sheet` / `--z-sheet-nested` tokens; map the current
   `z-10/20/30/40` + the `zIndex` prop default onto them.
4. Remove dead `var(--stat-size, 2.5rem)` in StatCard (use the `text-stat` token) and the
   dead NavFab `console.debug` placeholder branch.
5. ActivityGrid weekday rail `fontSize: "0.625rem"` → a `text-micro` token (or reuse label).
6. Split RecordPicker.tsx: extract `useTilePressHandlers.ts`, `PickerTile.tsx` (from
   GYM-126), `ShowHiddenExpander.tsx`, `EmptyNewUserPrompt.tsx` → picker body ≤ ~450 lines.

## Acceptance criteria
- [x] Zero inline magic px/rem for the listed cases (grep-verified: no `88px`,
      `maxWidth:`, `0.625rem`, `--stat-size`, numeric `zIndex={` / `z-20` left in
      src); tokens defined once in tokens.css + mapped in tailwind.config.js.
- [x] RecordPicker.tsx 1139 → 467 lines (<500); behavior-identical per
      tsc/lint/tests + build; on-device manual smoke still pending (review gate).

## Comments

### 2026-06-12T09:55:00Z — task created
Sequence after/with GYM-126 (same files) — one PR train, small commits.

### 2026-06-12T15:30:00Z — implemented (agent wave 5a)

**Tokens (tokens.css + tailwind.config.js):**
- `--tile-h: 88px` → Tailwind spacing token `tile` → `h-tile` utility (same
  idiom as `h-header`/`h-nav`); all 8 inline `style={{height:"88px"}}` sites
  replaced (picker tiles, + Muscle tile, Show-all tile, both skeleton grids).
  The index.css `.picker-tile-grid-*` comment that referenced --tile-h is now true.
- `--chip-max: 8rem` + `--chip-max-wide: 10rem` → `max-w-chip` /
  `max-w-chip-wide`. Decision: kept TWO tokens rather than flattening DayCard's
  10rem — the history list has more horizontal room than in-sheet header rows,
  and flattening would be a visual change (this wave is behavior-identical).
  3 sites replaced (SetLogger, HistoryDay, DayCard) — 4th site from the review
  was consolidated away in an earlier wave.
- z-scale: `--z-chrome: 20` / `--z-sheet: 30` / `--z-sheet-nested: 40` →
  `z-chrome` class on AppHeader + BottomNav; BottomSheet's `zIndex?: number`
  prop replaced by `layer?: "sheet" | "sheet-nested"` (default "sheet"),
  style references the CSS vars; ManageSheet passes `layer="sheet-nested"`
  (was `zIndex={40}`). NavFab z-10 / AppShell z-10 / SheetSaveButton z-10 /
  ActivityGrid's selected-cell zIndex:1 stay local per task scope.
- StatCard: dead `var(--stat-size, 2.5rem)` removed → existing `text-stat`
  token (identical 2.5rem / line-height 1).
- `text-micro` fontSize token (0.625rem, lh 1, label letter-spacing) replaces
  both ActivityGrid inline `fontSize:"0.625rem"` rails (weekday + month) —
  computed style identical to the old `text-label leading-none` + inline override.
- NavFab: dead console.debug placeholder branch removed → `onRecord?.()`.

**RecordPicker split (1139 → 467 lines):** extracted
- `useTilePressHandlers.ts` (91) — tap/long-press hook + LONG_PRESS_MS/MOVE_THRESHOLD_PX;
- `PickerTile.tsx` (74) — from GYM-126, consumes `h-tile`;
- `ShowHiddenExpander.tsx` (63);
- `EmptyNewUserPrompt.tsx` (122) — §12.6 empty-new-user JSX, callbacks via props;
- plus, needed to actually get under 500 (the four listed extracts alone left
  ~590): `MusclePanel.tsx` (220) + `ExercisePanel.tsx` (230) — the two
  slide-track panels as presentational components — and `usePickerData.ts`
  (199) — the read-side queries + derivations (muscleByName, exerciseList,
  muscleOptions, ownedExerciseIds, continueExercise, §12.5 prefetches), JSX
  and derivations copied verbatim. RecordPicker keeps orchestration: UI state,
  mutations, handlers, manage sheets.

**Also (file-size rule "every touched file <500"):** useRecord.ts 571 → 322 by
moving the manage-element hooks (rename/delete/hide/move/unhide + hidden
lists) to `hooks/useManageElements.ts` (281), re-exported from useRecord so no
import site changes; ManageSheet.tsx 539 → 485 by extracting
`ManageMoveView.tsx` (89) + the GYM-126 rename-error dedup.

**Verification:** bench `tsc --noEmit` + `eslint --max-warnings 0` +
`vitest run` (93 passed) + `vite build` green; `wc -l`: no src file >500
(largest: ManageSheet 485, RecordPicker 467). Grep for the listed magic values
returns nothing. On-device smoke pending — left in `review`.

**Suggested commit:** `Tokenize tile, chip, z-index sizes; split RecordPicker`

**Overlap with GYM-126 (one PR train):** tokens here are consumed by GYM-126's
PickerTile (`h-tile`) and SetLogger (`max-w-chip`); RecordPicker.tsx is touched
by both. Land this token commit first, then the GYM-126 dedup commit, or merge
as one train.
