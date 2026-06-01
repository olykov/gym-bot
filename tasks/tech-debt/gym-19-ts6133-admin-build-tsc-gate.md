---
schema_version: 1
id: GYM-19
title: "Fix TS6133 unused imports so the admin build runs the tsc gate"
slug: gym-19-ts6133-admin-build-tsc-gate
status: done
priority: low
type: chore
labels: [tech-debt, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T09:40:00Z
start_date: 2026-06-01T15:00:00Z
finish_date: 2026-06-01T15:02:00Z
updated: 2026-06-01T15:02:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-8]
commits: ["147e92e"]
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
- [x] `tsc --noEmit` clean in apps/admin
- [x] Dockerfile build stage uses `npm run build`

## Comments

### 2026-06-01T09:40:00Z — task created
Deferred during GYM-8. Cosmetic/safety; no runtime impact.

### 2026-06-01T15:02:00Z — done (committed, not yet deployed)
Only 3 TS6133s, all the unused default `React` import (tsconfig jsx=react-jsx → automatic runtime,
no React in scope needed): Dashboard.tsx (line removed), MyTraining.tsx + Training.tsx (dropped
`React,` keeping `{ useEffect, useState }`). Restored Dockerfile build stage to `npm run build`
(tsc && vite build). Verified locally: `tsc --noEmit` clean; full `npm run build` passes (1418
modules, built in 1.40s). Committed 147e92e. Awaiting operator push (rebuilds admin-frontend image).
