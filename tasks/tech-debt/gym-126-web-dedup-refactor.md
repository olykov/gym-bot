---
schema_version: 1
id: GYM-126
title: "apps/web dedup: PickerTile, useWeightRepsForm, SetFigure, queryKeys factory, BottomNav measure hook"
slug: gym-126-web-dedup-refactor
status: review
priority: medium
type: refactor
labels: [frontend, refactor, dx]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:50:00Z
start_date: 2026-06-12T15:30:00Z
finish_date: null
updated: 2026-06-12T15:30:00Z
epic: tech-debt
depends_on: [GYM-124]
blocks: []
related: [GYM-127]
commits: []
tests: ["apps/web/src/api/queryKeys.test.ts"]
design_reports: ["docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-126 — Dedup refactor (review doc 02 §3)

## Problem
Copy-paste pairs and triplets accumulated through GYM-82…GYM-115. No behavior change wanted —
pure consolidation, guarded by GYM-124's tests.

## Solution
1. `MuscleTile` ≡ `ExerciseTile` and `HiddenMuscleTile` ≡ `HiddenExerciseTile`
   (RecordPicker.tsx) → one `<PickerTile>` (+ `muted` variant).
2. Weight/reps form state triplicated (SetLogger / SetEditor / AddSetInline) →
   `useWeightRepsForm(initial?)` returning stepper props + `valid` + `reset`. Home for the
   shared `WEIGHT_STEP = 2.5` constant.
3. Recap row (SetLogger) vs `<SetRow>` typography duplication → display-only `<SetFigure>`;
   SetRow composes it.
4. Query keys: `src/api/queryKeys.ts` factory; replace the scattered string-array keys in
   useAnalytics/useRecord/useTraining and ALL invalidation call sites. Behavior-identical
   (preserve TZ suffixes + prefix-invalidation semantics) — document the prefix contracts
   in the module.
5. `BottomNav`: merge the duplicated measure effects into `useIndicatorPosition(activeIndex)`.
6. (From GYM-116, if not done there) replace the `Container` cloneElement stagger with CSS
   `:nth-child` delays — coordinate to avoid double work.

## Acceptance criteria
- [x] No visual/behavior change — code-identical refactor verified by tsc/lint/tests;
      on-device manual smoke of record/history/progress flows still pending (review gate).
- [x] Lint + tests green (93 tests, +7 new queryKeys contract tests); no new file >500
      lines. Net LOC: every deduplicated call site shrank (SetLogger 399→382, SetEditor
      324→307, AddSetInline 209→186, RecordPicker tiles −163); repo total is roughly
      flat because the new factory/hook files carry full JSDoc + a new test file.

## Comments

### 2026-06-12T09:50:00Z — task created

### 2026-06-12T15:30:00Z — implemented (agent wave 5a)

Behavior-identical dedup, all five solution items done (item 6 verified already
done in wave 3a — Container stagger is CSS-only `.reveal-stagger > :nth-child`,
no cloneElement; not redone).

**Files (new):**
- `apps/web/src/api/queryKeys.ts` (143) — central typed key factory; every key
  `as const`; `*Prefix` exports document the invalidation contracts in JSDoc
  (incl. the previously-unwritten rule that tz-suffixed `summary`/`activity`/
  `days` keys are invalidated by their tz-less prefixes).
- `apps/web/src/api/queryKeys.test.ts` (168) — 7 contract tests locking the
  EXACT pre-factory key shapes + prefix→key coverage (cache behavior frozen).
- `apps/web/src/hooks/useWeightRepsForm.ts` (115) — shared weightText/repsText
  + parseNumeric + valid mechanics; returns spreadable `weightProps`/`repsProps`
  (WEIGHT_STEP baked in), identity-stable `reset`. Call-site semantics composed
  on top: SetEditor keeps its changed-from-original check, AddSetInline its
  lastSet pre-fill + `!isPending` gate, SetLogger its §12.3 pre-fill effect
  (untouched — still fills only empty fields via the same text state).
- `apps/web/src/components/ui/SetFigure.tsx` (30) — the `{w}kg × {r}` display
  figure + muted `— · —` unknown variant; composed by SetRow and SetLogger recap.
- `apps/web/src/components/record/PickerTile.tsx` (74) — MuscleTile≡ExerciseTile
  and HiddenMuscleTile≡HiddenExerciseTile merged into one component with a
  `muted` variant (dashed border, --hint, opacity-70, isPending "Unhiding…",
  tap inert). Exact class strings preserved per variant (incl. press-95 only on
  the default variant, as shipped).

**Files (modified):** SetRow.tsx, SetLogger.tsx, SetEditor.tsx, AddSetInline.tsx,
BottomNav.tsx (the two duplicated measure effects merged into one
`useIndicatorPosition(activeIndex)` hook — measure + rAF re-measure + resize in
a single useLayoutEffect), useAnalytics.ts / useTraining.ts / useRecord.ts (all
key literals + ALL invalidation call sites now go through queryKeys;
`daysKey`/`dayKey`/`logContextKey` re-exported as factory aliases so no import
breaks — HistoryDay's `dayKey` usage untouched), ManageSheet.tsx (duplicated
rename onError mapping deduped into `renameErrorMessage`).

**Decisions:**
- Key factory reads DEVICE_TZ itself (module-level, same as before — DEVICE_TZ
  is a load-time constant), so call sites can't forget the tz suffix.
- `topExercisesPrefix(muscle?)` / `logContextPrefix(m?, e?)` /
  `exerciseProgressPrefix(m?, e?)` encode the two invalidation widths that were
  previously hand-typed prefixes.
- `useIndicatorPosition` now runs the rAF re-measure on every route change (was
  first-mount only) — same final indicator rect, strictly more robust; visually
  identical.

**Verification:** bench `tsc --noEmit` + `eslint --max-warnings 0` + `vitest run`
(93 passed, was 86 — +7 new) + `vite build` all green. Grep confirms zero
remaining hand-typed query-key string arrays outside `queryKeys.ts`.
On-device smoke (record/history/progress) pending — left in `review`.

**Suggested commit:** `Dedup web tiles, set forms, figures and query keys`

**Overlap with GYM-127 (one PR train, same session):** PickerTile.tsx consumes
the GYM-127 `h-tile` token; RecordPicker.tsx/SetLogger.tsx are touched by both
(126: PickerTile/SetFigure/form-hook; 127: tokens + file split). Land GYM-127's
token commit first, then this dedup commit, or merge as one train.
