---
schema_version: 1
id: GYM-60
title: "Contract: GET /analytics/top-muscles (muscles by my frequency) + regen clients"
slug: gym-60-top-muscles-contract
status: backlog
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-61, GYM-62]
related: [GYM-12]
commits: []
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
