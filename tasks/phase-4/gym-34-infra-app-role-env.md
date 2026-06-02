---
schema_version: 1
id: GYM-34
title: "Infra: app_rw env/secrets, role creation in deploy, alembic stamp runbook"
slug: gym-34-infra-app-role-env
status: todo
priority: high
type: chore
labels: [phase-4, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: null
finish_date: null
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32]
blocks: []
related: [GYM-11]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-34 — Infra: app_rw env/secrets, role creation in deploy, alembic stamp runbook

## Problem
The new `app_rw` role + `APP_DB_*` env must be wired through compose/ansible/CI, the role created
on the host idempotently from a secret, and the one-time prod `alembic stamp` documented.

## Plan
- Add `APP_DB_USER` (default `app_rw`) + `APP_DB_PASSWORD` to ansible `.env` render, both compose
  files, and the bot is unaffected. Add `APP_DB_PASSWORD` to CI/Actions secrets list (doc only;
  operator sets the secret value).
- Deploy step: run the GYM-32 idempotent role-bootstrap SQL against `gymbot_db` (creates `app_rw`
  NOSUPERUSER NOBYPASSRLS LOGIN with the secret password; re-runnable).
- Alembic runs as `myuser` (MIGRATION_DATABASE_URL); app runs as `app_rw`.
- Runbook (docs): prod one-time `cd packages/db && alembic stamp 0001_baseline` BEFORE first
  `alembic upgrade head`; rollback = `downgrade` + revert app to `myuser`.

## Acceptance criteria
- [ ] `docker compose config` valid on both files with the new env.
- [ ] Role bootstrap is idempotent (safe to re-run every deploy).
- [ ] Runbook documents stamp + rollback.

## Comments

### 2026-06-02T00:00:00Z — task created
Password is a secret — never committed; comes from env only.
