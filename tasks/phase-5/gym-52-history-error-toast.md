---
schema_version: 1
id: GYM-52
title: "apps/web: surface a 'couldn't save — restored' message on mutation error"
slug: gym-52-history-error-toast
status: in_progress
priority: low
type: bug-fix
labels: [phase-5, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T21:35:00Z
start_date: 2026-06-08T22:50:00Z
finish_date: null
updated: 2026-06-04T21:35:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-52 — Surface mutation-error message in History

## Problem
GYM-49's set edit/delete are optimistic and roll back correctly on error, but the rollback is SILENT —
spec §11.4/§11.7 require a non-scary "couldn't save — restored" message so the user understands why
the value reverted. Without it a failed save looks like the app ignored the edit.

## Plan
Add a lightweight token-only toast/inline message (reuse `<ErrorState>` styling) fired from the
`onError` of the edit/delete mutations in `hooks/useTraining.ts` / `SetEditor.tsx`. Respect
reduced-motion. No new library.

## Acceptance criteria
- [ ] A failed edit/delete shows a brief "couldn't save — restored" message; build green.

## Comments

### 2026-06-04T21:35:00Z — task created
Flagged during the GYM-49 review. Minor (error-only path); does not block the History push.
