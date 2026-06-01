---
schema_version: 1
id: GYM-24
title: "CI/deps hygiene: actions/checkout@v4 + bump yanked aiohttp"
slug: gym-24-ci-deps-hygiene
status: done
priority: medium
type: chore
labels: [tech-debt, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T09:40:00Z
start_date: 2026-06-01T10:00:00Z
finish_date: 2026-06-01T10:05:00Z
updated: 2026-06-01T10:05:00Z
epic: tech-debt
depends_on: []
blocks: []
related: []
commits: ["f2b8edd"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-24 — CI/deps hygiene: actions/checkout@v4 + bump yanked aiohttp

## Problem
- `.github/workflows/ci.yaml` uses `actions/checkout@v3` and `docker/login-action@v2`, which run on
  Node.js 20 — deprecated, forced to Node.js 24 on GitHub runners starting 2026-06-16. Every run
  currently emits the deprecation annotation.
- `apps/bot/requirements.txt` pins `aiohttp==3.11.13`, a YANKED release (regression, aio-libs #10617).

## Plan
- Bump `actions/checkout@v3 -> v4` and `docker/login-action@v2 -> v3` in ci.yaml.
- Bump `aiohttp` to 3.11.18+ (still within aiogram 3.28's `<3.14,>=3.9` range) in apps/bot/requirements.txt.

## Acceptance criteria
- [ ] No Node.js 20 deprecation annotations in CI
- [ ] aiohttp is a non-yanked version

## Comments

### 2026-06-01T09:40:00Z — task created
Flagged across earlier deploys. The actions deadline (2026-06-16) makes the checkout bump time-bound.

### 2026-06-01T10:05:00Z — done
infra-engineer: actions/checkout@v3->v4 (x4 jobs), docker/login-action@v2->v3 (x3), aiohttp 3.11.13->
3.11.18 (within aiogram 3.28.2 range). YAML valid; constraint checked. Committed f2b8edd locally; will
push bundled with GYM-23 so they share one deploy.
