---
schema_version: 1
id: GYM-76
title: "API: enforce name validation (reusable validator) on all muscle/exercise create paths + tests"
slug: gym-76-name-validation-api
status: in_progress
priority: high
type: feature
labels: [phase-5, api, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:40:00Z
finish_date: null
updated: 2026-06-05T12:00:00Z
epic: phase-5
depends_on: [GYM-75]
blocks: []
related: [GYM-74]
commits: []
tests: []
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
