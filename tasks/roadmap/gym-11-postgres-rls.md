---
schema_version: 1
id: GYM-11
title: "Phase 4: Postgres Row-Level Security"
slug: gym-11-postgres-rls
status: backlog
priority: high
type: feature
labels: [phase-4, security, db]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
depends_on: [GYM-10]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-11 — Phase 4: Postgres Row-Level Security

## Problem
Per-user isolation is hand-written WHERE clauses; no DB-enforced RLS.

## Plan
Dedicated low-privilege role; ENABLE/FORCE RLS on user-owned tables; policies on current_setting('app.user_id'); API sets SET LOCAL per request.

## Comments

### 2026-05-31T16:00:00Z — task created
Requires the single-owner API (GYM-9/10) first.
