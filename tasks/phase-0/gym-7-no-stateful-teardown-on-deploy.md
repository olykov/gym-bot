---
schema_version: 1
id: GYM-7
title: "Stop tearing down Postgres/Redis on every deploy"
slug: gym-7-no-stateful-teardown-on-deploy
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

# GYM-7 — Stop tearing down Postgres/Redis on every deploy

## Problem
Ansible deploy does state: absent -> present on the whole stack, so the DB/Redis go down on every push to main.

## Plan
Change the playbook to cycle only app services (bot/api/admin); never bring stateful services down. Verify on a deploy.

## Comments

### 2026-05-31T16:00:00Z — task created
Removes downtime per deploy.
