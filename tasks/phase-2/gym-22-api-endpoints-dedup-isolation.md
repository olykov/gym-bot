---
schema_version: 1
id: GYM-22
title: "apps/api endpoint coverage + de-dup isolation + unify ID"
slug: gym-22-api-endpoints-dedup-isolation
status: done
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: 2026-06-01T08:50:00Z
finish_date: 2026-06-01T09:30:00Z
updated: 2026-06-01T09:30:00Z
epic: phase-2
depends_on: [GYM-21]
blocks: []
related: [GYM-9, GYM-23]
commits: ["186050a"]
tests: []
design_reports: []
review_reports: []
review:
  security-auditor: pass-with-fixup
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

### 2026-06-01T09:30:00Z — done (builder + reviewer + fixup)
core-api-engineer added 20 contract routes (apps/api/app/api/v1/{bot,exercises,analytics}_router.py),
centralized per-user visibility in app/services/visibility.py (used by all listing endpoints, no inline
WHERE), and unified training.id to uuid4().hex. security-auditor reviewed: the NEW code was clean
(every endpoint scoped by JWT sub, IDOR-safe, no injection), but flagged PRE-EXISTING cross-user vulns
in the legacy router (PUT /muscles/{id}, PUT /exercises/{id} = write IDOR; GET /exercises, GET /training
= cross-user read) that the new routers did not shadow. core-api-engineer fixed: all 7 unscoped legacy
catalog routes now Depends(require_admin) (which correctly checks role=admin); removed a duplicate
get_current_user. Verified: docker build of admin_backend + in-container import OK (42 routes registered).
Committed 186050a. Remaining hardening (non-blocking) tracked as GYM-23. Additive — the live bot is
untouched (still direct SQL until Phase 3 / GYM-10).
