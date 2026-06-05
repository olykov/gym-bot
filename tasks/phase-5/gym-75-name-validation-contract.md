---
schema_version: 1
id: GYM-75
title: "Contract+docs: canonical name-validation rules (muscle/exercise) on all create schemas + validation.md"
slug: gym-75-name-validation-contract
status: in_progress
priority: high
type: feature
labels: [phase-5, api-contract, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:00:00Z
finish_date: null
updated: 2026-06-05T12:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-76, GYM-77]
related: [GYM-74]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-75 — Name validation: contract + canonical rules doc

## Problem
Muscle/exercise names have NO validation today — arbitrary length & characters are accepted, then blow
up the UI everywhere (tiles, record header, history, charts). Operator wants a professional, systemic
foundation (more input validation will follow). The contract is the platform source of truth, so the
constraints must be encoded there + documented once for all layers (API enforces, frontend mirrors).

## Canonical name rules (THE source of truth — author these verbatim)
Applies to every muscle/exercise NAME accepted on input (create/rename, any client).
- **Normalize:** trim leading/trailing whitespace; collapse internal whitespace runs to a single space.
- **Length (after normalize):** min 1; **muscle max 30**; **exercise max 40**.
- **Allowed characters:** Unicode letters (`\p{L}`, incl. Cyrillic), digits (`\p{N}`), space, and the
  punctuation set `- ' . , ( ) / & + °`. Everything else (control chars, emoji, `<>{}[]|\^~$@#…`)
  rejected — this also keeps names safe to render in Telegram HTML/Markdown.
- **Empty / whitespace-only → rejected.** Violations → HTTP 422 with a clear, field-named message.

## Plan (api-contract-guardian)
1. In `packages/api-contract/openapi.yaml`, add to the `name` field of EVERY create/input schema that
   carries a muscle or exercise name — `MuscleCreate`, `ExerciseCreate`, `ExerciseCreateByName`,
   `AdminExerciseCreate` (and any sibling): `minLength: 1`, `maxLength: 30` (muscle) / `40` (exercise),
   and a `pattern` implementing the allowed-char set (anchored, Unicode). Add a `description` pointing to
   docs/validation.md. Purely additive (tightening an unconstrained string is non-breaking at the schema
   level; document it as a validation addition).
2. Create `docs/validation.md` — "Input validation rules" — seed it with the **Name rules** table above
   (the canonical reference the API + frontend both cite). Structure it so future field rules append
   cleanly (it will grow: other inputs, numeric fields, etc.).
3. `make validate` + regen both clients (`make gen-python`, `make gen-typescript`); confirm they compile
   and the new constraints appear in the generated models.

## Acceptance criteria
- [ ] All muscle/exercise name input schemas carry minLength/maxLength/pattern per the canonical rules.
- [ ] docs/validation.md exists with the Name rules table. Both clients regenerated + compile. validate OK.

## Comments

### 2026-06-05T12:00:00Z — task created
Foundation for GYM-76 (API enforcement) + GYM-77 (frontend input mirror + display truncation).
