---
schema_version: 1
id: GYM-3
title: "Monorepo restructure to apps/packages/infra"
slug: gym-3-monorepo-restructure
status: done
priority: high
type: refactor
labels: [phase-1, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T13:26:15Z
start_date: 2026-05-31T13:26:15Z
finish_date: 2026-05-31T13:26:15Z
updated: 2026-05-31T13:26:15Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: ["bfacfb1"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-3 — Monorepo restructure to apps/packages/infra

## Problem
Mixed top-level layout blocked clean boundaries and parallel work.

## Solution
Moved app->apps/bot, admin_panel/backend->apps/api, admin_panel/frontend->apps/admin, init.sql->packages/db, ansible->infra/ansible, scripts/. Fixed compose/CI/ansible paths. Deployed first-try.

## Comments

### 2026-05-31T13:26:15Z — migrated
Deployed successfully (run 26714344923). Imports unchanged (package-root preserved).
