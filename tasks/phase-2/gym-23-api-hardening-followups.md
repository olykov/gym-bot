---
schema_version: 1
id: GYM-23
title: "apps/api hardening follow-ups from GYM-22 security review"
slug: gym-23-api-hardening-followups
status: done
priority: medium
type: chore
labels: [phase-2, security, tech-debt]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T09:30:00Z
start_date: 2026-06-01T09:50:00Z
finish_date: 2026-06-01T10:10:00Z
updated: 2026-06-01T10:10:00Z
epic: phase-2
depends_on: []
blocks: []
related: [GYM-22]
commits: ["7b306ab"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-23 — apps/api hardening follow-ups from GYM-22 security review

## Problem
The GYM-22 security-auditor review surfaced non-blocking hardening items (the must-fix IDOR/leaks were
already fixed in GYM-22). These remain.

## Plan
- **/admin/* prefix**: move the legacy admin catalog routes (now `require_admin`) under the `/admin/*`
  prefix the contract specifies. Removes the path collisions with the new user routes (e.g. POST
  /exercises, GET /training) and the reliance on FastAPI mount-order shadowing for safety. Coordinate
  with the admin frontend's API calls (apps/admin) since paths change.
- **CORS**: `allow_origins=["*"]` with `allow_credentials=True` in apps/api/main.py — tighten to the
  real admin/miniapp origins.
- **Debug prints**: remove `print()` of auth/token-derivation material in apps/api/app/core/auth.py
  (leaks to logs).
- **Type smell**: `Training.user_id == user_data["sub"]` compares a string sub against a BigInteger
  column in user_router.py / router.py — cast to int like the new bot_router does (brittle, not a leak).

## Acceptance criteria
- [ ] Legacy admin routes under /admin/* (or a documented decision to keep current paths)
- [ ] CORS restricted to real origins
- [ ] No auth-material prints in core/auth.py
- [ ] sub compared as int consistently

## Comments

### 2026-06-01T09:30:00Z — task created
Logged from the GYM-22 review. Non-blocking; the cross-user IDOR/leak must-fixes were resolved in GYM-22.

### 2026-06-01T10:10:00Z — done (two agents, coordinated)
core-api-engineer (apps/api) + client-frontend-engineer (apps/admin), coordinated on an exact path
contract. API: admin catalog moved to /api/v1/admin/* (7 routes, all require_admin) — collisions with
the user-facing GYM-22 routers eliminated (no more mount-order safety dependency); CORS now reads
CORS_ALLOW_ORIGINS (default https://gymbot.olykov.com), no more "*"+credentials; auth debug print()s
replaced with logger.debug (no secrets/tokens logged); JWT sub int-cast made consistent. Frontend:
admin pages (Muscles/Exercises/Training) repointed to /admin/*; user pages (MyTraining/TrainingModal)
left on /user/*. Verified: admin_backend builds + imports (42 routes, 7 /admin/*); apps/admin vite
build clean. Changes are all tightening (more restrictive), so no security re-review needed. Committed
7b306ab. Optional: set CORS_ALLOW_ORIGINS in prod env if origins differ from the default.
