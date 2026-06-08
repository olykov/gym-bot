---
schema_version: 1
id: GYM-99
title: "API: analytics resolve exercise/muscle by name_key + drop negative log-context cache + allow hiding OWN items"
slug: gym-99-analytics-namekey-resolution
status: in_progress
priority: critical
type: bug-fix
labels: [tax-fixes, api, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T15:00:00Z
start_date: 2026-06-08T15:00:00Z
finish_date: null
updated: 2026-06-08T15:00:00Z
epic: tax-fixes
depends_on: [GYM-84]
blocks: [GYM-100]
related: [GYM-85]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-99 — Analytics name_key resolution + no negative cache + hide-own

## Problem (live, prod-verified)
A resolved/existing exercise (e.g. Bench press id=7 with 333 sets) opens in the SetLogger with NO PR /
history — "looks new"; the first set becomes the PR. DB is clean (verified on prod). Root causes:
1. Analytics resolve the exercise/muscle by EXACT name (`Exercise.name == :exercise`,
   `Muscle.name == :muscle`) — NOT by `name_key` (GYM-84). Any name variance → no match → empty.
2. `get_log_context` CACHES the empty/negative result (`cache_set(empty)` when exercise_id is None),
   keyed by name → one miss poisons the cache for the TTL.
3. Operator decision: own exercises/muscles must be Hide-able too (an own item WITH history can't be
   deleted by the delete-guard, so without Hide it's stuck in the picker). Today hide is global-only.

## Plan (core-api-engineer; app_name_key is already live on prod from GYM-84 — no migration)
- **name_key resolution:** in `analytics_router.py`, change every single-exercise/single-muscle name
  filter to match by key: `Muscle.name_key == app_name_key(:muscle)` AND
  `Exercise.name_key == app_name_key(:exercise)` (use the SQL fn, don't reimplement). Covers
  `_resolve_exercise_id` and the inline filters in completed-sets, personal-record, max-reps,
  exercise-progress, log-context, and any sibling that resolves ONE exercise by name. (Aggregations that
  GROUP BY name — top-muscles/top-exercises — are out of scope.) Centralize if practical.
- **No negative cache:** in `get_log_context`, when `exercise_id is None`, return the empty LogContext but
  do NOT `cache_set` it (or cache with a tiny TTL) so a miss never poisons. Keep caching the positive result.
- **Hide own items:** allow `PUT /muscles/{id}/hidden` and `PUT /exercises/{id}/hidden` to hide the
  caller's OWN item (not just globals), and ensure the visibility service (`visible_muscles` /
  `visible_exercises_for_muscle`) excludes hidden rows for ANY ownership (own + global). Unhide already
  handled by the create-resolve path (GYM-85) + the existing unhide endpoint.

## Acceptance criteria
- [ ] log-context/PR/completed-sets resolve by name_key (a variant like "bench-press"/"BENCH PRESS"
      returns the canonical exercise's real PR/history); empty results never cached/poison; hiding an OWN
      item removes it from the picker (unhide restores); tests + full apps/api suite green (0 failed).

## Comments

### 2026-06-08T15:00:00Z — task created
Prod-verified: data intact (Bench press id=7, 333 sets). The "looks new" symptom is name-resolution +
negative-cache, not data loss. Hide-own per operator decision.
