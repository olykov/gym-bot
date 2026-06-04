---
schema_version: 1
id: GYM-61
title: "API: implement top-muscles (frequency); top-exercises returns all for a muscle"
slug: gym-61-top-muscles-api
status: backlog
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: [GYM-60]
blocks: [GYM-62]
related: [GYM-12, GYM-59]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-61 — API: top-muscles + all-exercises

## Problem
Implement the frequency-sorted muscle list; confirm exercises can be returned in full (not top-5).

## Plan
- `GET /analytics/top-muscles` in apps/api (mirror `get_top_exercises`): for the caller,
  `SELECT m.name, count(*) freq FROM training t JOIN muscles m ON m.id=t.muscle_id WHERE t.user_id=:uid
  GROUP BY m.name ORDER BY freq DESC`. RLS-scoped via `get_principal`; cached (analytics cache);
  sargable (uses idx_training_user_muscle from GYM-59, or the user_id index).
- `GET /analytics/top-exercises`: confirm a large/absent `limit` returns ALL the user's exercises for
  the muscle frequency-sorted (the Progress picker passes a high limit). Adjust if it hard-caps.
- Tests: top-muscles order + counts + isolation; top-exercises returns all for a muscle.

## Acceptance criteria
- [ ] top-muscles correct (frequency desc, per-user); top-exercises can return all; tests green; sargable.

## Comments

### 2026-06-05T01:00:00Z — task created
Cache key per user; reuse the analytics cache + invalidation already wired.
