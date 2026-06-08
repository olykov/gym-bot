---
schema_version: 1
id: GYM-102
title: "Contract+API: list hidden muscles/exercises for the user (powers Show Hidden) + confirm hide-own muscle"
slug: gym-102-list-hidden-api
status: in_progress
priority: high
type: feature
labels: [tax-fixes, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T16:30:00Z
start_date: 2026-06-08T17:00:00Z
finish_date: null
updated: 2026-06-08T16:30:00Z
epic: tax-fixes
depends_on: []
blocks: [GYM-103]
related: [GYM-99]
commits: [3d46c1c]
tests: []
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
- [ ] list-hidden endpoints for muscles + exercises; hide-own muscle confirmed; clients regenerated;
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
