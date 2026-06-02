---
schema_version: 1
id: GYM-37
title: "RLS security fixups: reset legacy auth context, pin deps, prove propagation"
slug: gym-37-rls-security-fixups
status: todo
priority: high
type: bug-fix
labels: [phase-4, security, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T03:20:00Z
start_date: null
finish_date: null
updated: 2026-06-02T03:20:00Z
epic: phase-4
depends_on: [GYM-33, GYM-35]
blocks: []
related: [GYM-11, GYM-36]
commits: []
tests: []
design_reports: []
review_reports: [docs/reviews/2026-06-02-rls-security-review.md]
review: {}
backlog_ref: ""
---

# GYM-37 — RLS security fixups (from GYM-35 review)

## Problem
The GYM-35 security review returned SAFE WITH FIXUPS. Two HIGH items must be closed before prod.

## Plan
- **H1** — `apps/api/app/middleware/permissions.py`: make `get_current_user`, `require_role`,
  `require_admin` yield-based and call `reset_principal_context(...)` in `finally`, mirroring
  `get_principal`. No route may leave `app.role`/`app.user_id` set after the request.
- **H2** — pin `anyio` and `starlette` in `apps/api/requirements.txt` (currently unpinned transitive)
  so contextvar-propagation behavior cannot silently change; rely on GYM-36 to PROVE that the GUC
  inside a real query equals the caller for both `get_principal` and `require_*`, and that
  admin-then-user on one worker does not leak.
- **M4** — add a pre-deploy data assertion (in the runbook + a GYM-36 test): no catalog row with
  `is_global AND created_by IS NOT NULL`.

## Acceptance criteria
- [ ] Legacy auth deps reset context (no stale principal possible).
- [ ] anyio/starlette pinned.
- [ ] GYM-36 asserts per-path GUC == caller + admin/user no-leak + M4 data check; suite green.

## Comments

### 2026-06-02T03:20:00Z — task created
Carved from the GYM-35 review. H1 is a clear code defect; H2/M4 are proof + pinning.
