---
schema_version: 1
id: GYM-26
title: "Core API: service-token auth + scoped user impersonation"
slug: gym-26-service-auth-impersonation
status: done
priority: high
type: feature
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: 2026-06-01T11:30:00Z
updated: 2026-06-01T11:30:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-10, GYM-28]
commits: ["2e77855"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-26 — Core API: service-token auth + scoped user impersonation

## Problem
The bot needs to call the Core API on behalf of Telegram users it has already authenticated. There is no service-to-service auth path; sharing JWT_SECRET would be insecure.

## Plan
Add a single resolve_principal() layer in apps/api that yields (user_id, role) from EITHER a user JWT (Authorization: Bearer) OR a service identity: header X-Service-Token == BOT_SERVICE_TOKEN (constant-time compare) + X-Act-As-User: <id> -> role is ALWAYS 'user' (never admin). BOT_SERVICE_TOKEN is a required env setting. Wire the bot-facing GYM-22 endpoints to this layer; admin endpoints stay admin-JWT-only. RLS-ready: effective user_id is the single source for scoping.

## Comments

### 2026-06-01T11:00:00Z — task created
Decision B from the Phase 3 plan. security-auditor reviews this (impersonation = critical).

### 2026-06-01T11:30:00Z — done (security review pending after GYM-28)
core-api-engineer: get_principal() in permissions.py (~L45) — X-Service-Token via hmac.compare_digest
vs settings.BOT_SERVICE_TOKEN, then X-Act-As-User (int) -> Principal(user_id, role="user" HARDCODED, no
self-escalation); else user JWT (sub->user_id, role from claim); else 401. BOT_SERVICE_TOKEN is a
required fail-fast setting. All 22 bot-facing routes use get_principal; the 7 /admin/* routes stay
require_admin (JWT-only) — a service caller cannot reach them. Verified: py_compile, admin_backend build
+ in-container import (22 bot routes + 7 admin gated), fail-fast on missing token. Committed 2e77855.
Full auth-bridge security-auditor review will run after GYM-28 (bot side) so it covers end-to-end.
