---
schema_version: 1
id: GYM-102
title: "Contract+API: list hidden muscles/exercises for the user (powers Show Hidden) + confirm hide-own muscle"
slug: gym-102-list-hidden-api
status: review
priority: high
type: feature
labels: [tax-fixes, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T17:00:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-fixes
depends_on: []
blocks: [GYM-103]
related: [GYM-99]
commits: [3d46c1c, 883637a]
tests: [apps/api/tests/test_gym102_list_hidden.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-102 — List hidden (API) for Show Hidden

## Problem
A user can hide muscles/exercises (GYM-99) but there is no way to LIST what's hidden, so the frontend
can't offer a "Show Hidden → Unhide" affordance. Need a list-hidden read.

## Plan (api-contract-guardian → core-api-engineer; no migration)
- Add read endpoints to list the caller's hidden items:
  - `GET /muscles/hidden` → the muscles this user has hidden (Muscle[]).
  - `GET /exercises/hidden?muscle=<name>` (and/or unscoped) → the exercises this user has hidden, scoped
    to a muscle for the picker. (Decide the cleanest shape; mirror existing list endpoints + auth.)
- Confirm hiding an OWN muscle works end-to-end (GYM-99 made visibility exclude hidden for own + global;
  verify the hide endpoint accepts an own muscle). Unhide already exists (DELETE .../hidden).
- Regen both clients. Tests: hidden lists return exactly the user's hidden items; empty when none.

## Acceptance criteria
- [x] list-hidden endpoints for muscles + exercises; hide-own muscle confirmed; clients regenerated;
      tests + full apps/api suite green.

## Comments

### 2026-06-08T16:30:00Z — task created
Powers the Show Hidden / Unhide UX (GYM-103).

### 2026-06-08 — contract slice (api-contract-guardian)
Commit `3d46c1c`. Additive only; no breaking changes; no new schemas.

Added two read endpoints to `packages/api-contract/openapi.yaml`, mirroring the existing
muscle/exercise list endpoints (security `userJwt`/`serviceAuth` + `ActAsUser`, get_principal):
- `GET /muscles/hidden` (operationId `listHiddenMuscles`, tag `muscles`) → 200 `Muscle[]`
  (the muscles the caller has hidden), 401. No params beyond `ActAsUser`.
- `GET /exercises/hidden` (operationId `listHiddenExercises`, tag `exercises`) → 200 `Exercise[]`
  (the exercises the caller has hidden within a muscle), 401. Required `muscle` query param
  via the shared `MuscleNameQuery` (muscle NAME).

Regen + checks: `make validate` OK (36 paths, 38 schemas); `make gen-python` + `make gen-typescript`
regenerated. Python `models.py` regenerated (only timestamp delta — both endpoints reuse the
existing `Muscle`/`Exercise` schemas, so no new models); models import OK. TS `schema.ts`
regenerated (gitignored, not committed); `tsc --noEmit --strict` passes; both new operationIds and
paths appear in the schema.

Clients affected: TS clients (web/admin/miniapp) gain the two typed operations; Python bot client
models unchanged (hand-maintained `client.py` wrapper unaffected — additive, no migration).

Remaining (core-api-engineer, separate slice): implement the two endpoints in `apps/api` +
confirm hide-own-muscle end-to-end + tests.

### 2026-06-08 — API slice (core-api-engineer)
Commit `883637a`. 335 passed, 0 failed across the full `apps/api` test suite.

**GET /muscles/hidden** (`bot_router.py`): subquery over `user_hidden_muscles` for
the caller joins to `muscles`; ordered by name; `is_mine` populated (True only for
own private muscles); `resolution` null.

**GET /exercises/hidden?muscle=<name>** (`exercises_router.py`): muscle resolved
by `app_name_key(:muscle)` (variant case/dash/space-insensitive, consistent with
GYM-99); returns Exercise[] of hidden exercises under that muscle for the caller;
`is_mine` populated; `resolution` null; 404 when muscle name does not resolve;
empty array when nothing hidden.

**Hide-own-muscle confirmed end-to-end**: `PUT /muscles/{id}/hidden` has no
global-only guard (GYM-99 removed it); `visible_muscles` excludes hidden rows
regardless of ownership (GYM-99). Tests confirm: own muscle hides → absent from
`GET /muscles` → present in `GET /muscles/hidden` with `is_mine=True` → unhide
restores to visible list and removes from hidden list.

**Tests** (`tests/test_gym102_list_hidden.py`): 16 new tests across 3 classes
(`TestListHiddenMuscles`, `TestListHiddenExercises`, `TestHideOwnMuscleEndToEnd`)
with dedicated `USER_102_ID = 500102` seed. Full suite result: **335 passed, 0 failed**.
