---
schema_version: 1
id: GYM-6
title: "Remove hardcoded admin creds and default JWT secret in apps/api"
slug: gym-6-remove-hardcoded-admin-jwt
status: in_progress
priority: high
type: chore
labels: [phase-0, security]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-05-31T18:45:00Z
finish_date: null
updated: 2026-05-31T18:45:00Z
epic: phase-0
depends_on: [GYM-5]
blocks: []
related: [GYM-5]
commits: ["e445890"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-6 — Remove hardcoded admin creds and default JWT secret in apps/api

## Problem
apps/api has a hardcoded admin/olykov login and a default JWT secret fallback.

## Plan
Require JWT_SECRET and admin creds from env only; fail fast if unset. Wire secrets via deploy env.

## Comments

### 2026-05-31T16:00:00Z — task created
Do after GYM-5 so the secrets exist; otherwise prod login breaks.

### 2026-05-31T18:45:00Z — implemented (delegated), awaiting ADMIN_PASSWORD secret + deploy
Delegated by seam: core-api-engineer changed apps/api (config.py: JWT_SECRET/ADMIN_USER/ADMIN_PASSWORD
as required pydantic-settings fields + field_validators that fail fast at startup; auth.py: removed
hardcoded admin/olykov and the JWT default, now reads from settings). infra-engineer wired the three
secrets through .github/workflows/ci.yaml, infra/ansible/deploy.yaml (.env), and both compose files
(prod default fallback removed). Validated: ansible syntax-check + both compose config OK; rg confirms
no hardcoded admin/JWT default remains.

BLOCKED ON OPERATOR: secret ADMIN_PASSWORD is NOT yet set (only ADMIN_USER/JWT_SECRET/DB_PASSWORD
exist). apps/api fails fast without it, so the push is held. Once ADMIN_PASSWORD is added, push ->
the deploy applies the new admin creds + JWT + the rotated DB_PASSWORD in one go -> verify -> close.
