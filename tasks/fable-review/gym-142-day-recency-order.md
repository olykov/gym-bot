---
schema_version: 1
id: GYM-142
title: "Order GET /training/day exercises by recency so Continue is correct cross-session"
slug: gym-142-day-recency-order
status: done
priority: medium
type: feature
labels: [api, freshness, record]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:00:00Z
start_date: 2026-06-12T09:00:00Z
finish_date: 2026-06-12T19:51:15Z
updated: 2026-06-12T19:51:15Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-139]
commits: [92b5474]
tests: [apps/api/tests/test_gym141_142_day_detail.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-142 — /training/day recency ordering (Continue residual)

## Problem
GYM-139 fixed the in-app Continue tile via a session override. RESIDUAL: on a fresh sheet open / after
logging via the bot, there is no session override, and the client falls back to `exs[0]` — which is the
server's ALPHABETICAL order (`training_id` is a UUID, so the client cannot derive recency). So Continue is
wrong cross-session.

## Solution (server)
`GET /training/day/{date}` (`training_history_router.py`) should order the day's exercise GROUPS by recency
(most recently logged first) so the client's `exs[0]` fallback is the latest. SIDE EFFECT: this also changes
the History day-detail display order to "most recent exercise on top" (currently alphabetical) — operator
must confirm this is acceptable (it is arguably better). Sets WITHIN an exercise keep set order.

## Status
Awaiting operator decision on the day-display order side effect (most-recent-first vs keep alphabetical).
If declined, the in-app session override (GYM-139) is the only fix and this task is cancelled.

## Comments

### 2026-06-12T09:00:00Z — created
Residual of GYM-139. Needs operator's OK on the day-order side effect before launch.

### 2026-06-12T19:51:15Z — done (variant A approved, backend implemented)
Implemented on branch `fix/gym-141-142-impl`, commit `28ba3fa`.

Recency key used: `training.date` (TIMESTAMP column, set to server UTC at insert time via
`datetime.utcnow()` / `NOW()`). The query adds an `ex_recency` CTE that computes
`MAX(date) AS last_logged` per exercise_id for the queried day, then orders the outer result
`ORDER BY er.last_logged DESC, t.set ASC`. This puts the most-recently-logged exercise first;
sets within each exercise remain in ascending set-number order.

The `date` TIMESTAMP column is the correct and only available per-row recency signal in the
`training` table (no `created_at` exists; `id` is a hex UUID with no embedded time). Rows moved
via `PATCH /training/{id}/move` get noon-UTC of the target date, so their recency within the day
is fixed at 12:00:00 UTC — this is a known trade-off accepted by the design.

Full suite: 460 passed, 0 failed, 0 skipped (real postgres:16, Docker up). Suite includes three
new recency-order tests plus six new is_pr tests (GYM-141 backend, same commit).
