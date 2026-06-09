---
schema_version: 1
id: GYM-93
title: "API: candidate search over canonical names + aliases (name_key + synonym + pg_trgm fuzzy), muscle-scoped"
slug: gym-93-candidate-search-api
status: done
priority: medium
type: feature
labels: [taxonomy, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-09T21:25:52Z
finish_date: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
epic: tax-i18n
depends_on: [GYM-108]
blocks: [GYM-94]
related: []
commits:
  - 1551ee09b052abfd353ce82d3e6b8e316a979a2b
  - 9a4f22d669db9d3ebbdd09e369a1fe64d7b21037
  - 4c9ab5953d730882a9f14db7af46a29ee8020390
tests:
  - apps/api/tests/test_gym93_exercise_search.py
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
- [x] Search returns ranked canonical candidates (key/alias/fuzzy) with i18n names; muscle filter works;
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

### 2026-06-10 — endpoint + migration implemented (core-api-engineer)

Server-side implementation complete on branch `i18n/gym-93-search`.

**Migration 0007** (`packages/db/alembic/versions/0007_pg_trgm.py`):
- `CREATE EXTENSION IF NOT EXISTS pg_trgm` (idempotent; requires superuser — Alembic runs as myuser).
- `CREATE INDEX IF NOT EXISTS idx_exercises_name_key_trgm ON exercises USING gin (name_key gin_trgm_ops)`.
- `CREATE INDEX IF NOT EXISTS idx_exercise_alias_name_key_trgm ON exercise_alias USING gin (name_key gin_trgm_ops)`.
- Chains after `0006_canonical_alias`. Idempotent `upgrade()`, proper `downgrade()`.

**Endpoint** (`apps/api/app/api/v1/exercises_router.py`):
- `GET /exercises/search` with the same session/RLS/GUC plumbing as all other exercise endpoints.
- Uses a single CTE query (`_SEARCH_SQL`) with four UNION ALL tiers; DISTINCT ON keeps the best
  tier per exercise id; final ORDER BY (tier rank, score DESC, name) then LIMIT.
- SQL uses `CAST(:param AS type)` form (not `::type` casts) to avoid psycopg2 parameter-parsing
  conflicts with `::` after parameter substitution.
- Fuzzy threshold: **0.3** (pg_trgm default). Balances typo tolerance vs. false positives for
  5–15 char exercise name catalog.
- Muscle filter and lang filter both use NULL-safe `CAST(:param AS type) IS NULL OR ...` pattern.

**Schema**: `ExerciseCandidate` added to `apps/api/app/schemas/schemas.py`.

**Tests** (`apps/api/tests/test_gym93_exercise_search.py`): 14 integration tests covering all
four tiers, muscle filter, limit, empty result, caller's own custom exercise searchability, RLS
isolation (other user's private exercise not visible), lang filter exclusion, and 401.

**Suite result**: 399 passed, 0 failed, 37 warnings (all pre-existing deprecation warnings).
DB was up (Docker postgres:16 ephemeral container via conftest); integration tests ran, not skipped.
