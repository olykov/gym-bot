---
schema_version: 1
id: GYM-19
title: "Fix TS6133 unused imports so the admin build runs the tsc gate"
slug: gym-19-ts6133-admin-build-tsc-gate
status: backlog
priority: low
type: chore
labels: [tech-debt, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T09:40:00Z
start_date: null
finish_date: null
updated: 2026-06-01T09:40:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-8]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-19 — Fix TS6133 unused imports so the admin build runs the tsc gate

## Problem
The GYM-8 production Dockerfile for apps/admin uses `npx vite build` instead of `npm run build`
because the `build` script runs `tsc && vite build` and source files have pre-existing TS6133
(unused import / variable) errors that fail `tsc`. The bundle is identical (Vite transpiles via
esbuild), but the type-check gate is currently skipped in the prod build.

## Plan
Remove the unused imports/vars in apps/admin/src so `tsc --noEmit` is clean, then restore the
Dockerfile build stage to `npm run build` (tsc && vite build) so type errors gate the prod image.

## Acceptance criteria
- [ ] `tsc --noEmit` clean in apps/admin
- [ ] Dockerfile build stage uses `npm run build`

## Comments

### 2026-06-01T09:40:00Z — task created
Deferred during GYM-8. Cosmetic/safety; no runtime impact.
