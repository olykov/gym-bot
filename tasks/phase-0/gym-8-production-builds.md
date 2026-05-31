---
schema_version: 1
id: GYM-8
title: "Production builds: drop dev servers in prod"
slug: gym-8-production-builds
status: backlog
priority: medium
type: refactor
labels: [phase-0, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-8 — Production builds: drop dev servers in prod

## Problem
admin frontend runs vite dev and admin backend runs uvicorn --reload in prod images.

## Plan
Multi-stage build: vite build + static serve (nginx/caddy) for admin; uvicorn without --reload for api.

## Comments

### 2026-05-31T16:00:00Z — task created
Needed before any horizontal scaling.
