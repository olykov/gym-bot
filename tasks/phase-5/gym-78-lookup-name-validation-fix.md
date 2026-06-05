---
schema_version: 1
id: GYM-78
title: "Fix: lookup-reference name fields must not enforce length/char limits (can't add exercise to pre-existing long-named muscle)"
slug: gym-78-lookup-name-validation-fix
status: in_progress
priority: critical
type: bug-fix
labels: [phase-5, api, api-contract, validation, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T13:30:00Z
start_date: 2026-06-05T13:30:00Z
finish_date: null
updated: 2026-06-05T13:30:00Z
epic: phase-5
depends_on: [GYM-75, GYM-76]
blocks: []
related: [GYM-77]
commits: []
tests: []
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
