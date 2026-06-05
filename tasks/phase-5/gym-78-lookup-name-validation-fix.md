---
schema_version: 1
id: GYM-78
title: "Fix: lookup-reference name fields must not enforce length/char limits (can't add exercise to pre-existing long-named muscle)"
slug: gym-78-lookup-name-validation-fix
status: done
priority: critical
type: bug-fix
labels: [phase-5, api, api-contract, validation, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T13:30:00Z
start_date: 2026-06-05T13:30:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-75, GYM-76]
blocks: []
related: [GYM-77]
commits: [ef0c5df, cd51a06]
tests: [apps/api/tests/test_gym78_lookup_name.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-78 — Lookup-reference names must not be length/char-capped

## Problem (live regression from GYM-75/76)
Operator can't add a NEW exercise into a PRE-EXISTING muscle whose name is > 30 chars:
`POST /api/v1/exercises` → 422. Cause: the exercise-create request validates `muscle_name`
(a REFERENCE to an existing muscle) with `validate_name(max_len=30)`. Reading/logging into long-named
records works (`POST /training` already lookup-tolerant), but the create-exercise path over-validates the
referenced muscle name.

**Principle:** length + allowed-char limits apply to a name being **CREATED/STORED**, never to a name used
only to **LOOK UP** an existing record — otherwise you can never reference data that predates the rules.

## Plan (parallel, disjoint dirs)

### API (core-api-engineer — apps/api)
- Add `validate_lookup_name(s: str) -> str` to `apps/api/app/schemas/validators.py`: normalize (trim +
  collapse) + reject empty/whitespace-only ONLY. No `max_len`, no char-whitelist (lookups are
  parameterized SQL → safe; a non-existent/odd name 404s at the DB anyway).
- Apply `validate_lookup_name` to the LOOKUP-reference fields:
  - `ExerciseCreateByName.muscle_name` (currently `validate_name(max_len=30)` — THE bug).
  - `TrainingCreate.muscle_name` + `TrainingCreate.exercise_name` — refactor the existing inline
    `_normalize_and_check_chars` to call the new shared `validate_lookup_name` (drop the now-redundant
    char-check for consistency; DRY).
- Keep FULL validation on CREATE-name fields: `MuscleCreate.name` (30), `ExerciseCreate.name` (40),
  `ExerciseCreateByName.name` (40).
- Tests (extend `apps/api/tests/test_gym76_name_validation.py` or a new file): creating an exercise whose
  `muscle_name` is a pre-existing 31+-char muscle SUCCEEDS (the exact regression); the NEW exercise `name`
  still capped at 40 (41 chars → 422); lookup name empty/whitespace → 422; FULL suite green (0 failed).

### Contract (api-contract-guardian — packages/api-contract)
- Remove `maxLength` AND `pattern` from the LOOKUP-reference name fields in `openapi.yaml`:
  `ExerciseCreate.muscle_name`, `TrainingCreate.muscle_name`, `TrainingCreate.exercise_name` (keep
  `minLength: 1` + a description noting "reference to existing record — not length/char-bound").
- Keep full constraints on CREATE-name fields (`MuscleCreate.name`, `ExerciseCreate.name`,
  `AdminExerciseCreate.name`).
- Update `docs/validation.md` to document the CREATE-vs-LOOKUP distinction explicitly.
- `make validate` + regen both clients; confirm the bot's python client can now construct an
  exercise-create with a >30-char muscle_name.

## Acceptance criteria
- [ ] Adding a new exercise into a pre-existing >30-char muscle returns 201/200, not 422.
- [ ] CREATE-name limits (muscle 30 / exercise 40 + char whitelist) still enforced; lookup names only
      normalized. Contract + API agree. docs/validation.md updated. API suite green; clients regenerated.

## Comments

### 2026-06-05T13:30:00Z — task created
Live regression caught via prod logs (repeated `POST /exercises` 422 against a long-named muscle).

### 2026-06-05 — API half done (commit cd51a06)
Added `validate_lookup_name(s: str) -> str` to `apps/api/app/schemas/validators.py`.
The function normalizes (trim + collapse) and rejects empty/whitespace-only input only —
no max-length cap, no `_NAME_RE` char-whitelist.  A 40-line docstring explains the
create-vs-lookup distinction (why it is safe without char/length caps: parameterized SQL,
non-matching names 404 at the DB layer).

Fields changed from `validate_name` to `validate_lookup_name`:
- `ExerciseCreateByName.muscle_name` — THE bug; was `validate_name(max_len=30)`.
- `TrainingCreate.muscle_name` + `TrainingCreate.exercise_name` — refactored the
  inline `_normalize_and_check_chars` validator to delegate to `validate_lookup_name`
  (dropped redundant inline char-check; DRY); validator renamed `_normalize_lookup_name`.

`schemas.py` imports cleaned: `_NAME_RE` and `normalize_name` removed (no longer used
directly), `validate_lookup_name` added.

CREATE-name caps kept unchanged: `MuscleCreate.name` (max 30), `ExerciseCreate.name`
(max 40, admin), `ExerciseCreateByName.name` (max 40 — the NEW exercise name).

Tests:
- `test_gym76_name_validation.py`: four tests that asserted the now-removed over-strict
  behaviour were updated to document the correct lookup behaviour (long/odd muscle names
  accepted in `ExerciseCreateByName.muscle_name` and `TrainingCreate` lookup fields).
- `apps/api/tests/test_gym78_lookup_name.py` added: `validate_lookup_name` unit tests,
  the exact GYM-78 regression (31-char muscle_name in `ExerciseCreateByName` → passes),
  41-char exercise name still rejected, empty lookup rejected, TrainingCreate long-name
  lookups pass, CREATE-name caps confirmed unchanged.

Full suite result: **243 passed, 0 failed**.

### 2026-06-05 — contract half done (commit ef0c5df)
Relaxed the three LOOKUP-reference name fields in `packages/api-contract/openapi.yaml` — removed
`maxLength` and `pattern`, kept `minLength: 1`, and updated each description to note "reference to
an existing record — normalized only, not length/char-bound":
- `ExerciseCreate.muscle_name`
- `TrainingCreate.muscle_name`
- `TrainingCreate.exercise_name`

Kept FULL constraints (`minLength`/`maxLength`/`pattern`) on the CREATE-name fields, untouched:
`MuscleCreate.name`, `ExerciseCreate.name`, `AdminExerciseCreate.name`.

`docs/validation.md`: added a "Create vs lookup" subsection to the Name rules (created names get
length+char limits; lookup-reference names are normalized only) and rewrote the per-schema
enforcement table to show the create-vs-lookup role and which constraints each field carries.

`make validate` passed (valid OpenAPI 3.1). Regenerated both clients (`make gen-python`,
`make gen-typescript`); Python models compile and TS schema type-checks under `tsc --strict`.
Python-client check: `ExerciseCreate(name=..., muscle_name=<52-char Cyrillic>)` now constructs
with no pydantic pattern/maxLength rejection on `muscle_name`; `TrainingCreate` accepts a 60-char
`exercise_name`; create-name still capped (41-char `name` → ValidationError); empty lookup name
rejected by `minLength: 1`.

Affected clients: bot (python `gym_api_client`) and web/admin/miniapp (TS `schema.ts`) — both
regenerated in this change. Change is permissive (relaxes a constraint), so non-breaking for
existing valid requests.
