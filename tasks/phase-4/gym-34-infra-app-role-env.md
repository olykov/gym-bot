---
schema_version: 1
id: GYM-34
title: "Infra: app_rw env/secrets, role creation in deploy, alembic stamp runbook"
slug: gym-34-infra-app-role-env
status: done
priority: high
type: chore
labels: [phase-4, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: 2026-06-02T03:05:00Z
finish_date: 2026-06-02T00:00:00Z
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32]
blocks: []
related: [GYM-11]
commits: [26d0faf]
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

### 2026-06-02T00:00:00Z — implementation complete (26d0faf)

Wired:
- APP_DB_USER (default app_rw) + APP_DB_PASSWORD added to admin_backend in
  docker-compose.yaml and docker-compose.local.yaml. Bot service and postgres
  service are unchanged.
- APP_DB_USER/APP_DB_PASSWORD added to ansible .env render in deploy.yaml
  (APP_DB_USER uses Jinja default('app_rw', true)).
- create_app_role.sql copied to host on every deploy; two new ansible tasks
  after docker_compose_v2: (1) wait for pg_isready, (2) idempotent role bootstrap
  via docker exec psql with no_log: true (password never in logs).
- APP_DB_PASSWORD threaded through ci.yaml Run Ansible Playbook env block with
  doc comment; operator must set it in GitHub Actions secrets.
- packages/db/RUNBOOK.md created with full prod cutover order (a-e) and rollback.

Validation:
- docker compose -f docker-compose.yaml config: OK
- docker compose -f docker-compose.local.yaml config: OK
- ansible-playbook --syntax-check: exit 0

Prod cutover order:
(a) Operator sets APP_DB_PASSWORD in GitHub Actions secrets.
(b) Deploy runs; Ansible bootstrap creates app_rw role (idempotent).
(c) ONE-TIME on prod: cd packages/db && DATABASE_URL=<myuser url> alembic stamp 0001_baseline
(d) Apply RLS: DATABASE_URL=<myuser url> alembic upgrade head
(e) API (already deployed) connects as app_rw; RLS is enforced.
Rollback: alembic downgrade -1 (drops policies), revert API to myuser by
removing APP_DB_PASSWORD secret and redeploying pre-GYM-33 API.
