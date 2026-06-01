---
schema_version: 1
id: GYM-22
title: "apps/api endpoint coverage + de-dup isolation + unify ID"
slug: gym-22-api-endpoints-dedup-isolation
status: backlog
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-01T08:00:00Z
epic: phase-2
depends_on: [GYM-21]
blocks: []
related: [GYM-9]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-22 — apps/api endpoint coverage + de-dup isolation + unify ID

## Problem
Per-user isolation (global/private/hidden muscles & exercises) is hand-written twice — raw SQL in the bot and SQLAlchemy in the admin API — and can drift; training IDs are md5 in the bot vs uuid4 in the API.

## Plan
Implement/extend apps/api endpoints to match the GYM-21 contract, with the isolation logic centralized in ONE place in apps/api. Unify training.id generation to a single scheme. Additive — the live bot keeps using direct SQL until Phase 3 (GYM-10).

## Comments

### 2026-06-01T08:00:00Z — task created
Delegated to core-api-engineer after the contract (GYM-21) is defined.
