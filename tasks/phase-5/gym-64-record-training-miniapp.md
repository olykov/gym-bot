---
schema_version: 1
id: GYM-64
title: "Record a training IN the Mini App (5-item nav + center + button + log flow)"
slug: gym-64-record-training-miniapp
status: done
priority: high
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T04:00:00Z
start_date: 2026-06-05T04:00:00Z
finish_date: 2026-06-06T08:00:00Z
updated: 2026-06-06T08:00:00Z
epic: phase-5
depends_on: [GYM-41, GYM-49]
blocks: []
related: [GYM-12, GYM-65]
commits: [d9171c9, 2f4baef, bd9b607, dfa1dd2]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-64 — Record training in the Mini App

## Problem
The Mini App can VIEW (Dashboard/Progress), BROWSE + EDIT (History), but CANNOT record a training —
logging is still bot-only (`/gym`). The operator wants to log a workout from the Mini App, fast.

## Intent (operator, 2026-06-05)
- Bottom nav → **5 items**: 2 left + center **+** + 2 right (Instagram-style). Center = a prominent
  **orange, raised, distinct-shape** button that opens the record flow (not a route).
- A **Profile** tab is added far-right for symmetry — **STUB for now, do not build** (placeholder).
- Tapping **+** opens a **record-training flow** that must be **super smooth, fast, easy** — far fewer
  taps than the bot's muscle→exercise→set→weight→reps.

## Approach
1. **GYM-65 (design, this wave):** frontend-design plugin in ultrathink → spec §12 proposal for the
   5-item nav + center FAB and the record flow. Operator reviews before any build.
2. (After approval) nav rebuild + record flow build (+ any small API additions like recent-exercises).

## Existing API (record largely possible already, RLS-scoped)
`POST /training` (TrainingCreate muscle_name/exercise_name/set/weight/reps), `GET /analytics/completed-sets`
(auto next set#), `GET /analytics/personal-record` (pre-fill/PR), `GET /analytics/top-muscles` +
`top-exercises` (frequency picking), `POST /muscles` + `POST /exercises` (add inline). Gap: no
cross-muscle "recent exercises" / last-set pre-fill endpoint (candidate addition for max smoothness).

## Comments

### 2026-06-05T04:00:00Z — task created
Bot flow = muscle→exercise→set#→weight→reps (5 picks/set). Mini App target: exercise (1 tap from
recents) → Save (pre-filled) → repeat. The bot stays; the Mini App becomes a first-class logger.

### 2026-06-06T08:00:00Z — closed (operator confirmed "всё отлично")
Umbrella epic for record-training in the Mini App. Delivered + live across GYM-65..GYM-79:
build (GYM-69), picker v2 (GYM-72), slide-nav + recap (GYM-74), name validation
(GYM-75/76/78), display truncation + Chip ellipsis (GYM-77/79). Representative commits linked.
Follow-ups (keyboard overlap, long-press rename/delete) tracked as new tasks.
