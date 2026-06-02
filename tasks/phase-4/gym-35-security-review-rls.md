---
schema_version: 1
id: GYM-35
title: "Security review: RLS isolation end-to-end"
slug: gym-35-security-review-rls
status: todo
priority: high
type: research
labels: [phase-4, security]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: null
finish_date: null
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32, GYM-33]
blocks: []
related: [GYM-11]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
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
