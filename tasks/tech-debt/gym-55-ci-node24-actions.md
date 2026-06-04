---
schema_version: 1
id: GYM-55
title: "CI: bump GitHub Actions for Node 24 (checkout, login-action) before the deadline"
slug: gym-55-ci-node24-actions
status: backlog
priority: medium
type: chore
labels: [tech-debt, infra, ci]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T23:55:00Z
start_date: null
finish_date: null
updated: 2026-06-04T23:55:00Z
epic: tech-debt
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

# GYM-55 — CI: Node 24 action bump

## Problem
Every "Build and Deploy" run warns: `actions/checkout@v4` and `docker/login-action@v3` run on Node 20,
which "will be forced to run with Node.js 24 by default starting **2026-06-16**" (Node 20 removed from
runners 2026-09-16). The current pinned versions may not run correctly under the forced Node 24 — a
real risk to the deploy pipeline in ~12 days from 2026-06-04.

## Plan
In `.github/workflows/ci.yaml` (5× `actions/checkout@v4`, 4× `docker/login-action@v3`):
- Bump `actions/checkout@v4` → the latest release that supports Node 24 (e.g. `actions/checkout@v5`,
  or a pinned `@v4.x` that ships the Node 24 runtime).
- Bump `docker/login-action@v3` → latest `@v3.x` (Node 24-capable) or the current major.
- Re-run a deploy and confirm the deprecation warning is gone and the pipeline still builds/deploys
  all four images (bot, admin-backend, admin-frontend, web-frontend).

## Acceptance criteria
- [ ] No Node-20 deprecation warning on a deploy run; build + deploy still green.

## Comments

### 2026-06-04T23:55:00Z — task created
Flagged from the Phase 5 deploy runs. Hard deadline 2026-06-16 (forced Node 24).
