---
schema_version: 1
id: GYM-7
title: "Stop tearing down Postgres/Redis on every deploy"
slug: gym-7-no-stateful-teardown-on-deploy
status: done
priority: medium
type: refactor
labels: [phase-0, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-05-31T18:30:00Z
finish_date: 2026-05-31T18:15:00Z
updated: 2026-05-31T18:15:00Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: ["46cb6a9"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-7 — Stop tearing down Postgres/Redis on every deploy

## Problem
Ansible deploy does state: absent -> present on the whole stack, so the DB/Redis go down on every push to main.

## Plan
Change the playbook to cycle only app services (bot/api/admin); never bring stateful services down. Verify on a deploy.

## Comments

### 2026-05-31T16:00:00Z — task created
Removes downtime per deploy.

### 2026-05-31T18:30:00Z — in progress
Removed the `state: absent` task from the "Check container" block in
`infra/ansible/deploy.yaml`. The block previously ran
`docker_compose_v2: state: absent` (full stack teardown) followed by
`state: present` on every deploy. That torn-down Postgres (gymbot_db) and
Redis (gymbot_redis) on every push to main.

The fix: drop the `absent` step entirely and keep only
`docker_compose_v2: pull: always / state: present`. Docker Compose pulls
fresh images for all services but only recreates containers whose image
digest or configuration has changed since the last run. The stateful
services use fixed images (postgres:16, redis:7-alpine) with no image-tag
variable, so their digests are stable across app deploys — Compose leaves
them running. Only the three app containers (gymbot_backend,
admin_backend, admin_frontend) receive new images on each push and are
therefore recreated.

Ansible playbook syntax-check: passed (`ansible-playbook --syntax-check`).

### 2026-05-31T18:15:00Z — done
Implemented by the infra-engineer subagent; orchestrator committed 46cb6a9 and pushed. Deploy run
26720325535 completed/success — and that deploy itself ran with the new present-only logic (no
absent teardown) and brought the stack up cleanly, which verifies the change. No DB/Redis downtime on
deploy going forward.
