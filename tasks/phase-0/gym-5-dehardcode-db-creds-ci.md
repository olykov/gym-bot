---
schema_version: 1
id: GYM-5
title: "Move hardcoded DB creds in ci.yaml to GitHub Secrets"
slug: gym-5-dehardcode-db-creds-ci
status: in_progress
priority: high
type: chore
labels: [phase-0, security]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-05-31T17:00:00Z
finish_date: null
updated: 2026-05-31T17:00:00Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: ["33876cf"]
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
Create GitHub Secrets and reference them in ci.yaml. Must match the existing Postgres role already
initialized in db_data (cannot rotate the value without a role migration).

## Comments

### 2026-05-31T16:00:00Z — task created
BLOCKED: operator handles this (needs creating the secrets and deciding on the existing role).
Claude to provide an exact how-to.

### 2026-05-31T16:45:00Z — how-to (operator)
Key constraint: the prod Postgres role/db in db_data was initialized as myuser / mypassword /
gym_bot_db. This step ONLY moves the values into GitHub Secrets — it does NOT change them, so the
live DB keeps working. (Rotating the password is a separate, later step — see below.)

Only DB_USER and DB_PASSWORD are real secrets. DB_HOST (gymbot_db) and DB_PORT (5432) are not secret
and stay inline. DB_NAME can go either way; moving it is optional tidiness.

Steps (run from the repo root):
1. Create the secrets with the SAME current values (do not change them):
     gh secret set DB_USER --body "myuser"
     gh secret set DB_PASSWORD --body "mypassword"
     gh secret set DB_NAME --body "gym_bot_db"
   (or add them in GitHub UI: Settings -> Secrets and variables -> Actions -> New repository secret)
2. Edit .github/workflows/ci.yaml deploy env (lines ~101-106) to reference ${{ secrets.* }}.
3. Secrets MUST exist BEFORE pushing (a push to main auto-deploys; empty secrets => broken DB auth).
4. Push -> watch "Build and Deploy" -> verify the bot still responds (same values, so connection is fine).

IMPORTANT — the leaked password lives in git history even after this edit. Removing it from the
current file does NOT purge history. So treat `mypassword` as compromised. The real fix is to ROTATE
it as a follow-up: ALTER USER myuser WITH PASSWORD '<new>'; on the prod DB, update the DB_PASSWORD
secret, redeploy. Track that under a follow-up task (or fold into GYM-6).

### 2026-05-31T17:00:00Z — ci.yaml edited (Claude), awaiting secrets
Edited .github/workflows/ci.yaml: DB_USER/DB_NAME/DB_PASSWORD now reference ${{ secrets.* }}
(DB_HOST/DB_PORT stay inline). Committed locally as 33876cf, NOT pushed. BLOCKED ON OPERATOR: create
the three GitHub Secrets with the current values, then push (push auto-deploys; empty secrets =>
broken auth). Once the operator confirms the secrets exist, push -> watch deploy -> verify bot, then close.
