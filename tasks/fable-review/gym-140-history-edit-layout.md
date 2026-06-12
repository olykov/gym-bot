---
schema_version: 1
id: GYM-140
title: "History: move/delete edit UI broken — fields blown out, buttons invisible, off-style"
slug: gym-140-history-edit-layout
status: in_progress
priority: high
type: bug-fix
labels: [frontend,design,history,bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: null
updated: 2026-06-12T08:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-140 — History: move/delete edit UI broken — fields blown out, buttons invisible, off-style

## Problem (operator, on-device review of the Fable batch)
- In History day-detail, editing is badly broken: **Move** — buttons not visible, fields blown out of
  layout, partially not even in our design system. Same for **Delete** — buttons not visible. Likely a
  Tailwind 4 migration regression in `MoveSetPanel` / `SetEditor` / `ManageMoveView` (classes that
  changed/dropped under TW4). Restore the layout + design-system styling; ensure all controls are visible
  and on-spec (docs/frontend-spec.md). ultrathink + frontend-design plugin. VERIFY visually.
