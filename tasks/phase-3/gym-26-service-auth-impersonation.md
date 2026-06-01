---
schema_version: 1
id: GYM-26
title: "Core API: service-token auth + scoped user impersonation"
slug: gym-26-service-auth-impersonation
status: in_progress
priority: high
type: feature
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: null
updated: 2026-06-01T11:00:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-10]
commits: []
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
