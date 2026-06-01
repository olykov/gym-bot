---
schema_version: 1
id: GYM-27
title: "Contract: document auth schemes + full Python client for the bot"
slug: gym-27-contract-auth-python-client
status: done
priority: high
type: feature
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: 2026-06-01T11:35:00Z
updated: 2026-06-01T11:35:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-10, GYM-28]
commits: ["4f3961a"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-27 — Contract: document auth schemes + full Python client for the bot

## Problem
The OpenAPI spec (GYM-21) describes operations but not the two auth schemes; the bot needs a usable async Python client, not just generated models.

## Plan
Add the two security schemes to packages/api-contract/openapi.yaml: a user bearer JWT, and a service auth (X-Service-Token + X-Act-As-User). Provide/generate a usable async Python client (httpx) with methods for the bot-facing operations, installable by the bot. Keep the Makefile generation reproducible. Additive.

## Comments

### 2026-06-01T11:00:00Z — task created
Independent of the API implementation; depends only on the agreed auth headers (decision B).

### 2026-06-01T11:35:00Z — done
api-contract-guardian: openapi.yaml now defines userJwt + serviceAuth (X-Service-Token) schemes + an
ActAsUser (X-Act-As-User int) header param, applied to all 20 bot-facing ops; admin/auth-me stay
userJwt-only; spec re-validated. New installable package gym-api-client (pyproject + async httpx
GymApiClient, 17 methods) injects X-Service-Token (constructor service_token=) and X-Act-As-User
(per-method act_as_user=) — exactly matching GYM-26's API. Verified via httpx MockTransport. Committed
4f3961a. Unblocks GYM-28.
