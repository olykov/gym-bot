---
schema_version: 1
id: GYM-37
title: "RLS security fixups: reset legacy auth context, pin deps, prove propagation"
slug: gym-37-rls-security-fixups
status: done
priority: high
type: bug-fix
labels: [phase-4, security, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T03:20:00Z
start_date: 2026-06-02T03:30:00Z
finish_date: 2026-06-02
updated: 2026-06-02T03:20:00Z
epic: phase-4
depends_on: [GYM-33, GYM-35]
blocks: []
related: [GYM-11, GYM-36]
commits: [594978a]
tests:
  - apps/api/tests/test_rls_endpoints.py
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

### 2026-06-02 — implementation complete (commit 594978a)

**H2 proof (step 1):** Running the new TestClient tests against the original contextvar approach produced `ValueError: Token was created in a different Context` inside `get_principal`'s `finally` block. This confirms the dep's `__enter__` threadpool call and `__exit__` threadpool call have different contextvar contexts (anyio's `copy_context()` is snapped separately for each `run_sync_in_worker_thread` call). The endpoint body's threadpool call got an empty GUC → 0 rows for all user queries.

**H2 fix (step 2):** Switched to `session.info` approach. `get_db(principal)` stashes `app_user_id`/`app_role` on `session.info`. The `after_begin` event reads from `session.info` (dict on the Session object, shared by reference across threadpool calls). Added `get_db_for_principal` / `get_db_for_admin` / `get_db_for_user` wrappers that inject the correct principal for each auth family. All routers updated.

**H1 fix (step 3):** `get_current_user`, `require_role`, `require_admin` are now yield-based generators. No contextvar manipulation remains in permissions.py — RLS state lives on session.info and is discarded at session close.

**M4 (step 4):** `TestCatalogM4DataGuard` added to `test_rls_endpoints.py`; pre-deploy SQL assertion added to `packages/db/RUNBOOK.md`.

**Pin (step 5):** `anyio==3.7.1` and `starlette==0.27.0` pinned in `requirements.txt` with explanatory comment.

**Final suite:** 47 passed (32 GYM-36 session-level + 15 GYM-37 HTTP-level). No failures.
