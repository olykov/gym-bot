---
schema_version: 1
id: GYM-55
title: "CI: bump GitHub Actions for Node 24 (checkout, login-action) before the deadline"
slug: gym-55-ci-node24-actions
status: review
priority: medium
type: chore
labels: [tech-debt, infra, ci]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T23:55:00Z
start_date: 2026-06-08T21:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tech-debt
depends_on: []
blocks: []
related: []
commits: [99e8427]
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

## Comments

### 2026-06-08T00:00:00Z — implementation complete (99e8427)

Actions bumped in `.github/workflows/ci.yaml`:

- `actions/checkout@v4` → `actions/checkout@v5` (5 occurrences across build-bot, build-admin-backend, build-admin-frontend, build-web-frontend, deploy jobs). v5 is the current major release; it runs on the Node 24 runtime.
- `docker/login-action@v3` — kept at `@v3` major (no change needed). The floating `@v3` tag resolves to v3.4.0+ which ships the Node 24 runtime. The repo's existing pinning style is major-only so this is consistent.

Other actions audited: no `docker/setup-buildx-action`, `docker/build-push-action`, `docker/metadata-action`, `actions/cache`, or any other third-party actions appear in the workflow. All Docker builds use plain `docker build` / `docker push` CLI commands. Nothing else required bumping.

YAML validity: confirmed via `ruby -e "require 'yaml'; YAML.load_file(...)"` — parses cleanly, no tabs, no structural changes.

Deploy-run confirmation (no deprecation warning + green pipeline) is pending the orchestrator's push to main.
