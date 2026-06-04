---
schema_version: 1
id: GYM-60
title: "Contract: GET /analytics/top-muscles (muscles by my frequency) + regen clients"
slug: gym-60-top-muscles-contract
status: done
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: 2026-06-05T01:05:00Z
finish_date: 2026-06-04T14:05:00Z
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-61, GYM-62]
related: [GYM-12]
commits: [df91882207dee60d5a3a4989c8eef4700d5cde3c]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-60 — Contract: top-muscles

## Problem
The Progress muscle picker must be ordered by the user's training frequency. Exercises already have
`GET /analytics/top-exercises?muscle&limit` (frequency-sorted) — reuse it (pass a large limit for
"all"). Muscles have no such endpoint.

## Plan
Add `GET /analytics/top-muscles` → `TopMuscle[]` = `{ name: string, frequency: integer }`
(reverse-frequency; muscles the user has trained), under the `get_principal` auth, tag `analytics`,
mirroring `/analytics/top-exercises` (sibling 401). Regenerate python + typescript clients. No change
to `top-exercises` (its `limit` param already returns all when set high).

## Acceptance criteria
- [ ] `top-muscles` in the spec; both clients regenerated + compile.

## Comments

### 2026-06-05T01:00:00Z — task created
Mirror the existing TopExercise shape.

### 2026-06-04T14:05:00Z — implemented (commit df91882)
Added `GET /analytics/top-muscles` to `openapi.yaml`, mirroring `GET /analytics/top-exercises`:
same `get_principal` security (`userJwt` + `serviceAuth` + `ActAsUser` param), tag `analytics`,
sibling `401 Unauthorized`. New schema `TopMuscle = { name: string, frequency: integer }`
(`frequency` = recorded session count for the muscle; reverse-frequency order), shape identical to
`TopExercise`. `/analytics/top-exercises` left untouched (its `limit` param already returns all).

Additive only — no breaking change. Clients affected: bot (python `gym_api_client`),
web/admin/miniapp (typescript schema). Both regenerated:
- `make validate` → OK (31 paths, 32 schemas).
- `make gen-python` → `TopMuscle` in `models.py`; imports + instantiates (`TopMuscle(name='chest', frequency=12)`).
- `make gen-typescript` → path `/analytics/top-muscles`, op `getTopMuscles`, type `TopMuscle` present;
  `tsc --noEmit --strict schema.ts` exit 0.

Git note: a concurrent GYM-59 run race-bundled these contract files into its commit; recovered via
soft-reset and re-committed GYM-60 in isolation (df91882, only `openapi.yaml` + `models.py`).
GYM-59's db migration was left untouched for that agent and is now committed separately.
