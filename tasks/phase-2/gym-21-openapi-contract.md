---
schema_version: 1
id: GYM-21
title: "OpenAPI contract + generated clients in packages/api-contract"
slug: gym-21-openapi-contract
status: done
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: 2026-06-01T08:00:00Z
finish_date: 2026-06-01T08:45:00Z
updated: 2026-06-01T08:45:00Z
epic: phase-2
depends_on: []
blocks: []
related: [GYM-9]
commits: ["4a9bdd2"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-21 — OpenAPI contract + generated clients in packages/api-contract

## Problem
There is no API contract; clients (bot, admin) each know the schema. Parallel client development needs a typed contract as the source of truth.

## Plan
Author an OpenAPI spec in packages/api-contract covering every data operation the bot performs today (users get/register; muscles list/add/hide; exercises list-by-muscle/add/hide/delete/top; training save/update/completed-sets/history/personal-record/max-reps) plus the admin's. Set up client generation: a Python client (for the bot, Phase 3) and a TS client (for web/admin). Spec is the source of truth; additive only.

## Comments

### 2026-06-01T08:00:00Z — task created
Delegated to api-contract-guardian. The orchestrator provides the exact operation list from the bot's DB layer.

### 2026-06-01T08:45:00Z — done
api-contract-guardian delivered packages/api-contract/openapi.yaml (OpenAPI 3.1, 25 paths, 22 schemas,
validated by openapi-spec-validator). Every bot postgres.py method maps to an operation (full table in
the agent report); existing apps/api endpoints also covered; schemas reuse apps/api shapes; per-user
scoping via the `sub` claim. Makefile + scripts generate Python (pydantic v2, for the bot) and TS clients;
Python sample committed, TS gitignored. Committed 4a9bdd2. Flagged gaps (additive if needed later):
get_latest_training(body_part) is subsumed by GET /analytics/history; muscle hide/delete are parity-only
with no bot method yet. This unblocks GYM-22.
