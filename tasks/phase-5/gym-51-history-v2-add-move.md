---
schema_version: 1
id: GYM-51
title: "History v2: add a set retroactively + move a set (date/exercise)"
slug: gym-51-history-v2-add-move
status: review
priority: low
type: feature
labels: [phase-5, frontend, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-09T00:00:00Z
finish_date: 2026-06-09T00:00:00Z
updated: 2026-06-09T12:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: [fba7842, 7c9ec86, 14f08e8, a33a411]
tests: [apps/api/tests/test_gym51_add_move.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-51 — History v2: add + move sets

## Problem
v1 (GYM-49) does view + edit weight/reps + delete. The operator wants, as the NEXT step, the ability
to add a set retroactively and move a set to another day/exercise.

## Plan (v2, after v1 ships)
- Add a set within a day/exercise (`POST /training` with an explicit date) — needs the create path to
  accept a date (today's create is `NOW()`); contract + API tweak.
- Move a set: change its `date` and/or `exercise_id` (a PUT extension or a dedicated endpoint) +
  cache invalidation. UX in the day-detail/editor.

## Acceptance criteria
- [ ] Add-set and move-set work end-to-end with isolation + cache invalidation.

## Comments

### 2026-06-04T18:00:00Z — task created
Deferred from the History plan (KISS); operator confirmed it's the planned next step after v1.

### 2026-06-09T00:00:00Z — contract slice (fba7842)
Contract-only slice of v2 landed in `packages/api-contract/`:

- RETROACTIVE ADD — added an OPTIONAL `date` (format `date`, naive-tolerant per GYM-30)
  field to `TrainingCreate`. When provided, the set is logged on that calendar day; when
  omitted the server uses now() (unchanged, backward-compatible). Additive, non-breaking.
- MOVE — added `PATCH /training/{training_id}/move` (operationId `moveTrainingSet`, tag
  `training`, userJwt/serviceAuth = get_principal). Existing PUT weight/reps edit untouched.
- `TrainingMove` request schema — all OPTIONAL: `date` (format `date`), `muscle_name` +
  `exercise_name` (lookup-name references, no length/char cap, mirroring `TrainingCreate`).
  At least one of {date, (muscle_name + exercise_name)} required (documented; full validation
  enforced in the API). Responses: 200 → `Training`; 401; 404 (set not found / not owned);
  409 (target day+exercise already has a set with the same set number — collision); 422
  (invalid body / nothing to move / target exercise not found).
- `make validate` passed (37 paths, 39 schemas). Regenerated both clients: Python models
  (`py_compile` OK — `date: date_aliased | None`, `TrainingMove` all-optional) and the
  TypeScript schema (`tsc --noEmit --strict` clean; `date?`, `TrainingMove`, `moveTrainingSet`
  present). TS schema is gitignored (regenerated on demand); Python models committed.

Affected clients: bot (Python), web/admin/miniapp (TypeScript) — additive `date` is safe to
adopt incrementally; `moveTrainingSet`/`TrainingMove` are new (no breaking change to existing
operations). API implementation of the new op + create-with-date is a separate (core-api) slice.

### 2026-06-09T00:00:00Z — API implementation slice (14f08e8)

Core API implementation of GYM-51 landed in `apps/api/`:

**Retroactive add (date storage — noon UTC)**
`TrainingCreate` gained an optional `date: Optional[_Date]` field (Pydantic type alias used to
avoid the `date` field-name / `datetime.date` type-name shadowing bug in Pydantic v2). When
`body.date` is supplied, `create_training` stores the row at `datetime.combine(body.date,
time(12, 0))` — noon UTC — which lands on the intended calendar day in every real-world timezone
(±12h safe). When omitted, `datetime.utcnow()` is used unchanged (backward-compatible).

**PATCH /training/{training_id}/move**
Added to `training_history_router.py` (co-located with DELETE and history reads). Logic:
1. Body validation: empty body → 422; only one of muscle_name/exercise_name → 422.
2. Fetch own row by (id, user_id) — RLS-scoped; not found or not owned → 404.
3. Resolve target date (noon UTC if `body.date` given) and target exercise
   (`resolve_exercise_id` own-first-then-global, name_key, variant-case safe) → 422 if not found.
4. Collision check (409): pre-query for another row with same (user_id, exercise_id, set, date
   day range) excluding the moving row. Defensive even if no DB unique constraint exists.
5. Apply `training.date`, `training.exercise_id`, `training.muscle_id`; commit; call
   `invalidate_user(uid)` (covers both source and target day analytics cache); return updated row.

**Tests** — `apps/api/tests/test_gym51_add_move.py` (15 tests):
- Retroactive add: past date stored at noon UTC and groups under that date in history; no date → utcnow window.
- Move date: stored at noon UTC of target day.
- Move exercise: by exact name and by variant case (UPPER/lower); both date+exercise at once.
- Validation: empty body → 422; only muscle_name → 422; only exercise_name → 422; nonexistent exercise → 422.
- Collision: 409 when target day+exercise+set already occupied by a different row.
- Ownership: nonexistent id → 404; cross-user → 404; unauthenticated → 401.
- Cache: `invalidate_user` called once with correct uid on success.

Full suite result: **385 passed, 0 failed**.

### 2026-06-09T12:00:00Z — frontend slice (a33a411)

Frontend implementation of GYM-51 landed in `apps/web/`:

**Add set retroactively (`<AddSetInline>`):**
A quiet `"+ Add set"` affordance appears after the last `<SetRow>` in each exercise group on the day
detail. Tapping expands an inline weight/reps form (two `<Stepper>` fields, pre-filled from the last
set of that exercise on that day). The next set number is derived client-side
(`max(existing set numbers) + 1`). On confirm: `POST /training {muscle_name, exercise_name, set,
weight, reps, date}`. The form is NOT in a separate sheet — it expands inside the card so the exercise
context remains visible. 409 collision surfaces as an inline error. On success: success haptic +
collapse. `useAddSet(date)` hook, invalidates the full cross-screen key set on settle.

**Move set (`<MoveSetPanel>` + `useMoveSet`):**
A **"Move"** action button added to the `SetEditor` header row (alongside the existing "Delete" — both
`--accent` text, ≥44px, right-aligned). Tapping Move swaps the sheet body to `<MoveSetPanel>` (the
exercise identity header stays so the user knows which set they are moving). The panel presents:
- A native `<input type="date">` pre-filled with the current day for the new date target.
- A muscle→exercise picker (same two-step tile pattern as `RecordPicker`): tapping "change" opens the
  muscle list (frequency-sorted via `useMuscles` + `useTopMuscles`), then the exercise list for the
  picked muscle (`useTopExercises` + `useExercises`). Back navigation works through the sub-steps.
- "Move set" sticky button (`SheetSaveButton`) — enabled when at least one of {date, exercise} has
  changed. Calls `PATCH /training/{id}/move`. 409 → graceful inline error. 422/404 → graceful error.
- Cancel returns to edit mode with no mutation.

`useMoveSet(sourceDate)` optimistically removes the set from the source day cache on `onMutate`,
rolls back on error, and on settle invalidates both the source day and the target day (if different),
plus all analytics keys (`summary`, `activity`, `exercise-progress`, `log-context`, `days`).

**`EditorTarget` type change (non-breaking):** `muscleName` field added (was previously not on the
type). All callers in `HistoryDay.tsx` updated to pass `ex.muscle_name` when opening the editor.

**Build result:** `tsc && vite build` — 730 modules, 0 errors, 0 warnings. Green.

**Needs live-device pass:**
- Add-set: verify the pre-fill correctly tracks the last set of the exercise (especially after a
  prior add within the same session before the cache refreshes).
- Move date: verify the native date picker behaves well in Telegram WebView on iOS/Android.
- Move exercise: verify the muscle/exercise picker scrolls correctly inside the non-fixedHeight
  BottomSheet body (the picker is not wrapped in a fixedHeight sheet, so the sheet should auto-expand
  to the content; if it clips, the sheet's max-height needs a review).
- 409 collision: needs a real conflicting row to verify the inline error message appears correctly.
