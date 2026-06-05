---
schema_version: 1
id: GYM-76
title: "API: enforce name validation (reusable validator) on all muscle/exercise create paths + tests"
slug: gym-76-name-validation-api
status: done
priority: high
type: feature
labels: [phase-5, api, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:40:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T13:00:00Z
epic: phase-5
depends_on: [GYM-75]
blocks: []
related: [GYM-74]
commits: [a57eb1d]
tests: [apps/api/tests/test_gym76_name_validation.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-76 — API: enforce name validation

## Problem
Enforce the canonical name rules (see docs/validation.md / GYM-75) at the API — the only DB owner, so
the authoritative enforcement point. Reject bad names with 422 before they reach the DB.

## Plan (core-api-engineer)
- Add ONE reusable validator in `apps/api` (e.g. `app/schemas/validators.py`): `normalize_name(s)` (trim
  + collapse whitespace) + `validate_name(s, *, max_len)` returning the normalized value or raising, using
  a compiled Unicode-aware pattern for the allowed-char set (`\p{L}\p{N}`, space, `- ' . , ( ) / & + °`).
  Prefer the `regex` module for `\p{L}` (add to requirements) OR an equivalent `re` solution that
  correctly accepts Cyrillic — verify with a Cyrillic test.
- Apply it via Pydantic v2 field validators to the `name` field of `MuscleCreate` (max 30),
  `ExerciseCreate` / `ExerciseCreateByName` / `AdminExerciseCreate` (max 40) in
  `apps/api/app/schemas/schemas.py` — reuse the single validator, don't duplicate logic. Normalized value
  is what gets stored (the trimmed/collapsed form).
- Invalid input → 422 (Pydantic) with a message naming the field + which rule failed.
- Tests (`apps/api/tests/test_gym76_name_validation.py`): empty/whitespace-only rejected; over-max
  rejected (30 muscle / 40 exercise boundary); disallowed chars (emoji, `<`, control) rejected; Cyrillic
  ACCEPTED; trim+collapse normalization applied to stored value; each create path covered.
- Canonical rules live in docs/validation.md (GYM-75) — match them exactly; do not invent different
  numbers. No DB CHECK constraint this round (existing rows already exceed it — would break); API +
  display is the enforcement.

## Acceptance criteria
- [ ] Reusable validator applied to all muscle/exercise name create paths; 422 on violation; Cyrillic OK;
      normalization stored; tests green; FULL `apps/api` suite green (0 failed).

## Comments

### 2026-06-05T12:00:00Z — task created
Depends on GYM-75 (canonical rules + contract). Runs after the contract lands.

## Comments

### 2026-06-05T13:00:00Z — implementation (core-api-engineer)

**Validator design**

Added `apps/api/app/schemas/validators.py` with:
- `MUSCLE_NAME_MAX = 30`, `EXERCISE_NAME_MAX = 40` — constants sourced from docs/validation.md.
- `normalize_name(s)` — trims leading/trailing whitespace, collapses internal runs to one space.
- `validate_name(s, *, max_len)` — normalizes, then enforces: non-empty, max_len, and the
  explicit character class `^[A-Za-z0-9À-ÖØ-öø-ÿА-яЁё \-'.,()/&+°]+$` (identical to the
  contract pattern — plain Python `re`, no extra dependency). Raises `ValueError` on failure so
  Pydantic surfaces a 422 with the field name.

**Schemas covered**

- `MuscleCreate.name` — `validate_name(max_len=30)` via `@field_validator("name", mode="before")`.
- `ExerciseCreate.name` — `validate_name(max_len=40)`. Admin path; `muscle` field is an int id,
  so no muscle_name to validate here.
- `ExerciseCreateByName.name` — `validate_name(max_len=40)`.
- `ExerciseCreateByName.muscle_name` — `validate_name(max_len=30)`.
- `TrainingCreate.muscle_name` + `TrainingCreate.exercise_name` — normalize + char-check only
  (see TrainingCreate decision below).

Note: `AdminExerciseCreate` is not present in this codebase — the admin router uses
`ExerciseCreate` (covered above). No other create/input schemas carrying a muscle or exercise
name were found via rg.

**TrainingCreate decision**

`TrainingCreate` is a lookup-only path: `POST /training` resolves muscle and exercise by name
and returns 404 if not found — it does not create new muscles or exercises. Enforcing the 40/30
char max here would reject valid lookups for names stored before this validation was introduced
(e.g., a "Global Bench Press" added by an admin before GYM-76). Therefore, max_len is NOT
enforced on TrainingCreate. Normalization (trim + collapse) and allowed-char rejection are still
applied: empty names would 404 anyway, and disallowed chars will never match a stored row.

**Pytest result**: 217 passed, 0 failed.
