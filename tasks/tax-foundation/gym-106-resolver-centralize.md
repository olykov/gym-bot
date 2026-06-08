---
schema_version: 1
id: GYM-106
title: "API: centralize exercise/muscle name→id resolver (own→global by name_key) + fix lingering exact-name sites — deployable, NO migration"
slug: gym-106-resolver-centralize
status: review
priority: high
type: refactor
labels: [tax-foundation, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T21:00:00Z
start_date: 2026-06-08T21:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-foundation
depends_on: []
blocks: [GYM-86]
related: [GYM-99]
commits: [57a128d]
tests: [apps/api/tests/test_gym106_resolver.py]
design_reports: [docs/adr/0002-canonical-layer.md]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-106 — Centralize the name→id resolver (safe prerequisite, NO migration)

## Problem
Per the impact map (ADR 0002), name→id resolution is scattered across 12 sites and a few still match EXACT
`.name` instead of `name_key` (a latent variant-name bug, missed by GYM-99): `top-exercises`
(analytics_router:278 muscle), `POST /exercises` muscle lookup (exercises_router:167), `POST /training`
(bot_router:516/524), legacy `POST /user/training` (router.py:255/260).

## Plan (core-api-engineer — deployable WITHOUT any migration; overrides come later in GYM-86)
- Add ONE shared helper `resolve_exercise_id(db, uid, muscle, exercise)` and `resolve_muscle_id(db, uid,
  muscle)` that match by `name_key` (`app_name_key`), DETERMINISTIC priority **own (created_by==uid) →
  global**. (The OVERRIDE branch is added later by GYM-86 once table 0005 is on prod — leave a clear seam.)
- Route the lingering EXACT-name sites + the existing `_resolve_exercise_id` through the shared helper, so
  all single-exercise/muscle resolution is one consistent, name_key, deterministic path.
- Pure consistency/robustness — no behavior change for canonical-name callers; variant names now resolve.
- Tests: variant-name training save resolves; top-exercises by variant muscle name; deterministic own-vs-
  global; full apps/api suite green. NO migration, deployable on its own.

## Acceptance criteria
- [ ] One shared name_key resolver (own→global, deterministic) used by all 12 resolution sites; lingering
      exact-name sites fixed; tests + full suite green; no migration needed.

## Comments

### 2026-06-08T21:00:00Z — task created (autonomous design session)
Carved out of GYM-86 as the safe, deployable, no-migration prerequisite (ADR 0002 rollout step 2). The
override-aware branch + effective-name display + rename-canonical frontend remain in GYM-86 (needs 0005).

### 2026-06-08T00:00:00Z — implemented (core-api-engineer)

**Resolver design.**
`apps/api/app/services/resolve.py` adds two public functions:
- `resolve_muscle_id(db, uid, muscle) -> int | None`: single ORM query filtered by
  `name_key == func.app_name_key(muscle)`, ordered by `(Muscle.created_by == None).asc()`
  (own rows sort before global rows), LIMIT 1.  Returns the id or None.
- `resolve_exercise_id(db, uid, muscle, exercise) -> int | None`: resolves the muscle
  first via the above, then resolves the exercise in the same own-first order.

**GYM-86 override seam.**  A clearly marked `TODO GYM-86:` comment sits between the own
lookup and the global lookup in each resolver.  The override-aware branch (checking
`user_muscle_override.display_name_key` / `user_exercise_override.display_name_key`) will
slot in there once migration 0005 is applied and GYM-86 is shipped.

**Sites centralized / exact-name fixes (from ADR 0002 LIST A).**
- `analytics_router._resolve_exercise_id` — body replaced to delegate to shared helper;
  signature extended with optional `uid`; `get_log_context` passes `uid` explicitly.
- `analytics_router.get_exercise_progress` — inline resolve replaced with shared helper.
- `analytics_router.get_top_exercises` (line ~278) — `Muscle.name == muscle` (EXACT) →
  `resolve_muscle_id(db, uid, muscle)` then filter by `muscle_id`.
- `bot_router.create_training` POST /training (lines ~516/524) — `Muscle.name ==` /
  `Exercise.name ==` (EXACT) → `resolve_muscle_id` / `resolve_exercise_id`.
- `exercises_router.create_exercise` POST /exercises (line ~167) — `Muscle.name ==`
  (EXACT) → `resolve_muscle_id`; create-on-miss preserved for GYM-85 flow.
- `router.create_user_training` legacy POST /user/training (lines ~255/260) —
  `Muscle.name ==` / `Exercise.name ==` (EXACT) → shared helpers.

Remaining sites already used name_key (analytics completed-sets / history / personal-record /
max-reps, bot POST /muscles).  Those were not changed.

**Full pytest result:** 352 passed, 0 failed (17 new GYM-106 tests + 335 pre-existing).
