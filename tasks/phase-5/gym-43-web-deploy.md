---
schema_version: 1
id: GYM-43
title: "Infra: apps/web Dockerfile + CI build + nginx route on gymbot.olykov.com"
slug: gym-43-web-deploy
status: backlog
priority: medium
type: chore
labels: [phase-5, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: [GYM-41]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-43 — Infra: build + deploy apps/web

## Problem
`apps/web` needs an image, a CI build job, and to be served on the current domain as the Mini App.

## Plan
- `apps/web/Dockerfile` (Vite build → nginx static), mirroring `apps/admin`.
- CI build job for `web-frontend` in `.github/workflows/ci.yaml`; compose `web_frontend` service.
- nginx on `gymbot.olykov.com`: serve `apps/web` at `/` (keep `/webhook` → bot). Keep `apps/admin`
  reachable (e.g. a temporary path) until its relocation task — DO NOT break admin in this cutover.
  Use the Docker-DNS resolver pattern (GYM-18) for the new upstream.

## Acceptance criteria
- [ ] web_frontend builds + deploys; `gymbot.olykov.com/` serves the Mini App; bot webhook intact.

## Comments

### 2026-06-04T09:00:00Z — task created
Admin relocation/embedding is a separate backlog task — out of scope here.
