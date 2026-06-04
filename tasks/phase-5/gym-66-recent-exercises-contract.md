---
schema_version: 1
id: GYM-66
title: "Contract: GET /analytics/recent-exercises (last-trained + last weight/reps) + regen clients"
slug: gym-66-recent-exercises-contract
status: done
priority: high
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: 2026-06-05T06:05:00Z
finish_date: 2026-06-04T19:15:00Z
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-67, GYM-69]
related: [GYM-64, GYM-65]
commits: [2a91e67]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-66 — Contract: recent-exercises

## Problem
The record flow's fast lane + cold-open pre-fill (spec §12.9) need the user's last-trained exercises
cross-muscle, with the last working set's weight/reps — one read. The contract has no such endpoint.

## Plan
Add `GET /analytics/recent-exercises?limit` (default ~8, capped ~50) → `RecentExercise[]`:
`RecentExercise = { muscle_name: string, exercise_name: string, last_weight: number, last_reps: number,
last_date: date }` — the user's most-recently-trained exercises, newest first. Under `get_principal`
auth, tag `analytics`, sibling 401. Naive-tolerant `date` (GYM-30). Regen python + typescript clients.

## Acceptance criteria
- [ ] endpoint + RecentExercise in the spec; both clients regenerated + compile.

## Comments

### 2026-06-05T06:00:00Z — task created
Powers the §12 fast lane (one read) + the cold-open pre-fill with the actual last working set.

### 2026-06-04T19:15:00Z — implemented (commit 2a91e67)
Added `GET /analytics/recent-exercises` to `openapi.yaml`, mirroring `GET /analytics/top-exercises`:
`get_principal` security (`userJwt` + `serviceAuth` + `ActAsUser` param), tag `analytics`, sibling 401.
Query param `limit` (integer, default 8, minimum 1, maximum 50). `200` → `RecentExercise[]`.

`RecentExercise = { muscle_name: string, exercise_name: string, last_weight: number, last_reps: number,
last_date: date (format: date, naive-tolerant per GYM-30) }` — all five required. The caller's
most-recently-trained distinct exercises, newest first, each carrying the last working set's
weight/reps and the date.

Additive only — no breaking change to existing paths/schemas.

Regen + verify:
- `make validate` → OK (32 paths, 33 schemas).
- `make gen` → python (datamodel-code-generator, pydantic v2, `--output-datetime-class datetime`) +
  typescript (`openapi-typescript@7`) regenerated.
- Python: `RecentExercise` imports and instantiates; `last_date` resolves to `datetime.date`.
- TypeScript: `tsc --noEmit --strict` on the generated schema passes; new path + `RecentExercise`
  type + `getRecentExercises` operation present.

Clients affected: bot (python `gym_api_client`) and web/admin/miniapp (typescript schema) — both
regenerated in the same change. Purely additive, so no client migration required.
