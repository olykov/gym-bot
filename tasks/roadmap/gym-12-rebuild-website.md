---
schema_version: 1
id: GYM-12
title: "Phase 5: Rebuild the website on the Core API"
slug: gym-12-rebuild-website
status: backlog
priority: medium
type: feature
labels: [phase-5, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: [GYM-4]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-12 — Phase 5: Rebuild the website on the Core API

## Problem
site_old hit Postgres directly with full-scan aggregations and no caching -- it could take down the server.

## Plan
Build apps/web against the API; cached/indexed aggregations; no pg in the frontend; sargable queries; pagination.

## Comments

### 2026-05-31T16:00:00Z — task created
The heavy site cannot recur by design.
