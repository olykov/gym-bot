---
schema_version: 1
id: GYM-107
title: "Deploy: apply Alembic migrations automatically (alembic upgrade head)"
slug: gym-107-auto-migrate-on-deploy
status: review
priority: high
type: chore
labels: [tech-debt, infra, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T00:00:00Z
start_date: 2026-06-10T00:00:00Z
finish_date: null
updated: 2026-06-10T00:30:00Z
epic: tech-debt
depends_on: []
blocks: [GYM-92]
related: [GYM-11, GYM-84]
commits: ["c6b3b8b"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-107 — Deploy: apply Alembic migrations automatically (alembic upgrade head)

## Problem
Migrations were applied **manually** on prod per `packages/db/RUNBOOK.md`; the deploy did not run
Alembic. Prod DB is at `0004_name_key`; `main`'s head is `0006_canonical_alias`. Manual steps are
error-prone and block shipping schema with a feature (e.g. tax-i18n needs `exercise_alias`).

## Solution
Add an on-deploy migration step to `infra/ansible/deploy.yaml`, run as the DB **superuser**, with the
app gated behind it. Variant 1 (throwaway container — no new image / CI job, host stays clean).

New deploy order: prep files → **ship `packages/db`** → **DB+Redis up** → wait DB → **bootstrap
`app_rw`** → **`alembic upgrade head`** → **app containers up**.

The migration runs as an ephemeral `--rm` `python:3.11-slim` container on `core-infra`:
`pip install -r requirements.txt && alembic upgrade head`.

### Security design (closed holes)
- **Superuser password never on the command line / in `ps`** — passed only via `--env-file {{work_dir}}/.env`.
- **Forced superuser identity** — `--env=DATABASE_URL=` (empty) makes `env.py` assemble the URL from
  `DB_*` (= myuser); an app_rw `DATABASE_URL` can never win precedence. `app_rw` cannot DDL anyway.
- **Read-only mount** of the alembic env (`:ro`) + `PYTHONDONTWRITEBYTECODE=1`.
- **Ephemeral, unprivileged** (`--rm`, no caps, no host mounts beyond `:ro` db dir).
- **Password masked** by SQLAlchemy (`***`) in any connection error → safe in deploy logs.
- **Supply chain**: `packages/db/requirements.txt` pins exact `alembic` / `sqlalchemy` / `psycopg2-binary`.
- **Ordering safety**: `app_rw` bootstrap precedes migration (migrations `GRANT` to it); migration
  precedes the app (new code never hits an un-migrated schema). Non-zero exit fails the deploy and
  leaves the previous app version running. Idempotent (`upgrade head` is a no-op at head).

## Acceptance criteria
- [ ] First deploy applies `0005` + `0006` to prod cleanly (additive, idempotent) and stamps head.
- [ ] Subsequent deploys with no new migration are a no-op (`changed=false`).
- [ ] A failing migration aborts the deploy without starting the new app.
- [ ] Password never appears in GitHub Actions logs.

## Comments

### 2026-06-10T00:00:00Z — start
Implemented: `deploy.yaml` restructured (DB→role→migrate→app), `packages/db/requirements.txt` pins
SQLAlchemy 2.0.23. Cannot be tested locally (no ansible/prod) — real validation is the first deploy,
which applies the already-committed `0005`/`0006` (canonical schema; additive, empty, unused by current
code; `0006.exercise_alias` is lang-aware and is exactly what tax-i18n needs). Holding push for the
operator's conscious OK to apply that schema to prod.

### 2026-06-10T00:30:00Z — deploy success, awaiting prod verification
Operator OK'd applying 0005/0006. Pushed `1220a45`; deploy run 27234332502 = **success**. Migration
task ran rc=0 in the correct order (ship db → DB/Redis up → bootstrap app_rw → alembic upgrade head →
app up). Reported `ok` not `changed`: `changed_when` checks stdout but alembic logs "Running upgrade"
to **stderr** — cosmetic only (rc=0 = success). FOLLOW-UP: change `changed_when` to read stderr; fold
into the next (tax-i18n) deploy rather than a cosmetic-only redeploy. Set to `review` pending operator
confirmation that prod `alembic_version` = `0006_canonical_alias` (cannot SSH prod under this task).
