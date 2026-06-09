---
schema_version: 1
id: GYM-93
title: "API: candidate search over canonical names + aliases (name_key + synonym + pg_trgm fuzzy), muscle-scoped"
slug: gym-93-candidate-search-api
status: in_progress
priority: medium
type: feature
labels: [taxonomy, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-09T21:25:52Z
finish_date: null
updated: 2026-06-09T21:25:52Z
epic: tax-i18n
depends_on: [GYM-108]
blocks: [GYM-94]
related: []
commits: [1551ee09b052abfd353ce82d3e6b8e316a979a2b]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-93 — Candidate search endpoint

## Problem
The add-exercise dropdown needs ranked canonical candidates as the user types. Per ADR 0001 (cheap layers
before AI).

## Scope (layers): contract + API. Per ADR 0003 (Channel B).
- New `GET /exercises/search?q=&muscle_id=&lang=&limit=` → ranked canonical candidates matched by
  name_key exact → prefix → `exercise_alias` hit (lang-aware) → `pg_trgm` fuzzy (typos). Return
  canonical exercise id, display name, muscle. Muscle-scoped when called from within a muscle, else
  whole catalog. `lang` comes from GYM-108 (Telegram language_code).
- Requires `CREATE EXTENSION IF NOT EXISTS pg_trgm` — migration `0007` (auto-applies on deploy via GYM-107).
- DECOUPLED from the seed: works over the 122 English canonical names with ZERO aliases; GYM-92 enriches.
- No embeddings here (that is GYM-96, the AI phase). pg_trgm only.

## Acceptance
- [ ] Search returns ranked canonical candidates (key/alias/fuzzy) with i18n names; muscle filter works;
      tests + suite green.

## Comments

### 2026-06-09 — contract added (api-contract-guardian)

Contract-only change on branch `i18n/gym-93-search` (commit `1551ee0`). Server impl + migration
0007 (`CREATE EXTENSION pg_trgm`) remain for core-api-engineer — status stays `in_progress`.

Added one additive, non-breaking operation to `packages/api-contract/openapi.yaml`:

- `operationId: searchExercises` — `GET /exercises/search`, tag `exercises`,
  `security: [{userJwt: []}, {serviceAuth: []}]` + the reusable `ActAsUser` header (same as the
  other user exercise endpoints).
- Query params: `q` (string, required, minLength 1); `muscle_id` (integer, optional — omit to
  search the whole catalog); `lang` (string, optional, ISO-639-1, e.g. `ru`, from GYM-108);
  `limit` (integer, optional, default 8, minimum 1, maximum 20).
- 200: array of `ExerciseCandidate`, best match first.

New schema `ExerciseCandidate` (all fields required):
- `id` (integer) — canonical exercise id, mirrors `Exercise.id`.
- `name` (string) — display name, mirrors `Exercise.name`.
- `muscle` (integer) — owning muscle id, mirrors `Exercise.muscle`.
- `muscle_name` (string) — owning muscle name, denormalized for display.
- `match_reason` (enum: `exact` | `prefix` | `alias` | `fuzzy`).
- `score` (number) — higher = better.

Ranking intent documented in the operation description: exact `name_key` -> prefix on `name_key`
-> alias (lang-aware on `exercise_alias.lang`) -> `pg_trgm` fuzzy. Works with zero aliases.

Clients regenerated via `make gen` (validate + python + typescript). Python model
`ExerciseCandidate` + `MatchReason` StrEnum committed in `clients/python/gym_api_client/models.py`.
TS types regenerate to `clients/typescript/schema.ts` (gitignored): `operations["searchExercises"]`
and `components["schemas"]["ExerciseCandidate"]` for apps/web. TS typechecks clean.
