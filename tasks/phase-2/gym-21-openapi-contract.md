---
schema_version: 1
id: GYM-21
title: "OpenAPI contract + generated clients in packages/api-contract"
slug: gym-21-openapi-contract
status: in_progress
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: 2026-06-01T08:00:00Z
finish_date: null
updated: 2026-06-01T08:00:00Z
epic: phase-2
depends_on: []
blocks: []
related: [GYM-9]
commits: []
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
