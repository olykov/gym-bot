---
schema_version: 1
id: GYM-6
title: "Remove hardcoded admin creds and default JWT secret in apps/api"
slug: gym-6-remove-hardcoded-admin-jwt
status: backlog
priority: high
type: chore
labels: [phase-0, security]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: phase-0
depends_on: [GYM-5]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-6 — Remove hardcoded admin creds and default JWT secret in apps/api

## Problem
apps/api has a hardcoded admin/olykov login and a default JWT secret fallback.

## Plan
Require JWT_SECRET and admin creds from env only; fail fast if unset. Wire secrets via deploy env.

## Comments

### 2026-05-31T16:00:00Z — task created
Do after GYM-5 so the secrets exist; otherwise prod login breaks.
