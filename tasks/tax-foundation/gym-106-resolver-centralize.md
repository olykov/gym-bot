---
schema_version: 1
id: GYM-106
title: "API: centralize exercise/muscle name→id resolver (own→global by name_key) + fix lingering exact-name sites — deployable, NO migration"
slug: gym-106-resolver-centralize
status: in_progress
priority: high
type: refactor
labels: [tax-foundation, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T21:00:00Z
start_date: 2026-06-08T21:30:00Z
finish_date: null
updated: 2026-06-08T21:00:00Z
epic: tax-foundation
depends_on: []
blocks: [GYM-86]
related: [GYM-99]
commits: []
tests: []
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
