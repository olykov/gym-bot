---
schema_version: 1
id: GYM-35
title: "Security review: RLS isolation end-to-end"
slug: gym-35-security-review-rls
status: review
priority: high
type: research
labels: [phase-4, security]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: 2026-06-02T03:10:00Z
finish_date: null
updated: 2026-06-02T03:20:00Z
epic: phase-4
depends_on: [GYM-32, GYM-33]
blocks: []
related: [GYM-11, GYM-37]
commits: []
tests: []
design_reports: []
review_reports: [docs/reviews/2026-06-02-rls-security-review.md]
review: {security-auditor: pass-with-fixup}
backlog_ref: ""
---

# GYM-35 — Security review: RLS isolation end-to-end

## Problem
RLS is security-critical; a gap = silent cross-tenant leak. Independent read-only audit required.

## Plan (read-only, report file:line)
- Confirm runtime role is `app_rw` (NOSUPERUSER, NOBYPASSRLS) and no superuser connection in app.
- Confirm ENABLE+FORCE RLS on all 6 tables and policies cover SELECT/INSERT/UPDATE/DELETE.
- Confirm fail-closed: unset GUC → 0 rows; empty-string cast handled.
- Confirm admin path only via verified admin-JWT; service token can never set role=admin.
- Confirm GUC is set with `is_local=true` and cannot leak across pooled connections.
- Note the FK-bypasses-RLS nuance and verify app only passes visible ids.
- Verify catalog write policy keeps global rows admin-only.

## Acceptance criteria
- [ ] Written review report; no critical/high findings open.

## Comments

### 2026-06-02T00:00:00Z — task created
Runs after GYM-32 + GYM-33 land on the branch.

### 2026-06-02T03:20:00Z — review complete: SAFE WITH FIXUPS
Report: docs/reviews/2026-06-02-rls-security-review.md. Architecture verified sound
(app_rw non-privileged; FORCE RLS on all 6 tables; fail-closed `nullif(...,'')::bigint`;
`is_local=true` GUC bound as params; bot cannot mint admin JWT; no GRANT TO PUBLIC). Two HIGH
fixups required before prod, tracked as GYM-37:
- H1: legacy auth deps (`get_current_user`/`require_admin`/`require_role`) set context but never
  reset it → stale-principal/admin-leak risk. Make them yield-based with finally-reset.
- H2: prove contextvar→after_begin propagation across the FastAPI threadpool (GYM-36 assertions:
  per-path GUC equals caller; admin-then-user on one worker no leak) + pin anyio/starlette.
Plus M4 (pre-deploy data check: no `is_global AND created_by IS NOT NULL` rows). M1/M2/M3/L*
are hardening, deferred. Done once GYM-37 fixups land and GYM-36 proves H2/M4.
