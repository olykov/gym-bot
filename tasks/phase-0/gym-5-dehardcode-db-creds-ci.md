---
schema_version: 1
id: GYM-5
title: "Move hardcoded DB creds in ci.yaml to GitHub Secrets"
slug: gym-5-dehardcode-db-creds-ci
status: blocked
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

# GYM-5 — Move hardcoded DB creds in ci.yaml to GitHub Secrets

## Problem
DB_USER/DB_PASSWORD (myuser/mypassword) are committed in .github/workflows/ci.yaml.

## Plan
Create GitHub Secrets and reference them in ci.yaml. Must match the existing Postgres role already initialized in db_data (cannot rotate the value without a role migration).

## Comments

### 2026-05-31T16:00:00Z — task created
BLOCKED: operator handles this (needs creating the secrets and deciding on the existing role). Claude to provide an exact how-to.
