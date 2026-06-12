---
schema_version: 1
id: GYM-142
title: "Order GET /training/day exercises by recency so Continue is correct cross-session"
slug: gym-142-day-recency-order
status: backlog
priority: medium
type: feature
labels: [api, freshness, record]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-12T09:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-139]
commits: []
tests: []
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
