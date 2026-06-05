---
schema_version: 1
id: GYM-75
title: "Contract+docs: canonical name-validation rules (muscle/exercise) on all create schemas + validation.md"
slug: gym-75-name-validation-contract
status: review
priority: high
type: feature
labels: [phase-5, api-contract, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T12:00:00Z
start_date: 2026-06-05T12:00:00Z
finish_date: 2026-06-05T12:35:00Z
updated: 2026-06-05T12:35:00Z
epic: phase-5
depends_on: []
blocks: [GYM-76, GYM-77]
related: [GYM-74]
commits: [0937064]
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

### 2026-06-05T12:35:00Z — implemented (commit 0937064)

**Schemas constrained** in `packages/api-contract/openapi.yaml` — `name` (and name-bearing
`*_name`) fields on every muscle/exercise create/input schema got `minLength: 1`, `maxLength`,
`pattern`, and a `description` pointing to docs/validation.md:

| Schema | Field | Kind | maxLength |
|--------|-------|------|-----------|
| `MuscleCreate` | `name` | muscle | 30 |
| `ExerciseCreate` | `name` | exercise | 40 |
| `ExerciseCreate` | `muscle_name` | muscle | 30 |
| `AdminExerciseCreate` | `name` | exercise | 40 |
| `TrainingCreate` | `muscle_name` | muscle | 30 |
| `TrainingCreate` | `exercise_name` | exercise | 40 |

No `ExerciseCreateByName` schema exists in the spec (the by-name create is `ExerciseCreate`,
which references the muscle by name — covered above). The `*_name` fields in response schemas
(`history`, `personal-record`) and the Telegram `first_name`/`last_name` identity fields are
NOT muscle/exercise names and were left untouched. Additive change (tightening an unconstrained
string).

**Pattern + Unicode caveat.** The canonical rule is `\p{L}/\p{N}` Unicode classes. The contract
validator (`openapi-spec-validator`, `format: regex`) compiles patterns with Python `re`, which
does NOT support `\p{L}`/`\p{N}`, so `make validate` rejected the property-escape form. Per the
task's documented fallback, I used an equivalent explicit class that still admits Cyrillic:

```
^[A-Za-z0-9À-ÖØ-öø-ÿА-яЁё \-'.,()/&+°]+$
```

- `A-Za-z` Latin, `À-ÖØ-öø-ÿ` Latin-1 letters (the `Ø`/`ö` splits exclude `×` U+00D7 and `÷`
  U+00F7), `А-яЁё` Cyrillic (incl. Ё/ё), `0-9` digits, space, and the punctuation set
  `- ' . , ( ) / & + °`.
- Verified it accepts Latin/Cyrillic/accented/`30°`/`(DB)`/`A/B & C` and rejects
  `<script>`, emoji, `{json}`, `a|b`, `a#b`, empty. This is the only compromise vs `\p{L}`
  (it covers Latin+Cyrillic+digits rather than all scripts); documented in docs/validation.md.

**docs/validation.md** created — "Input validation rules" with a **Name rules** section
(normalization, length, allowed-char tables, canonical regex, and a per-schema enforcement
table). Structured so future field families append as new sections.

**Quality gate.**
- `make validate` → OK (33 paths, 35 schemas).
- `make gen-python` → pydantic v2 models regenerated; all six fields carry `pattern`/`min_length`/
  `max_length`. Imported the client and confirmed it accepts valid Latin/Cyrillic names, rejects
  markup/emoji/empty, and enforces maxLength 30 (muscle) / 40 (exercise).
- `make gen-typescript` → `schema.ts` regenerated (types-only; `pattern`/`maxLength` are not
  expressed in TS types but the field descriptions are). `tsc --noEmit --strict` → exit 0.

**Affected clients:** Python (bot — runtime enforcement now via regenerated models) and
TypeScript (web/admin/miniapp — types regenerated; runtime mirroring lands in GYM-77).
