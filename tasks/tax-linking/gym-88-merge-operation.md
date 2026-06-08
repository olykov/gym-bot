---
schema_version: 1
id: GYM-88
title: "API/DB: merge canonical exercises (repoint user overrides + training A→B, leave redirect alias)"
slug: gym-88-merge-operation
status: backlog
priority: medium
type: feature
labels: [taxonomy, db, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-linking
depends_on: [GYM-87]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-88 — Merge operation

## Problem
Over time two canonical entries turn out to be the same; we must merge without losing data. Per ADR 0001
(merge is first-class, build early).

## Scope (layers): DB + API (admin/maintenance)
- A transactional merge(A→B): repoint all user overrides/links and all `training` referencing A to B; move
  A's aliases to B and add A's name as a redirect alias of B; deprecate A.
- Admin-only / service operation (not user-facing). Idempotent + audited.

## Acceptance
- [ ] merge(A→B) repoints all references + training, preserves history, leaves a redirect alias; covered by
      tests; suite green.
