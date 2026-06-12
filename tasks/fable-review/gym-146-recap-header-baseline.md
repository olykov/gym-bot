---
schema_version: 1
id: GYM-146
title: "TODAY / LAST TIME recap headers not on same baseline"
slug: gym-146-recap-header-baseline
status: done
priority: medium
type: bug-fix
labels: [frontend, ux, record, typography]
assignee: null
model: claude-sonnet-4-6
reporter: oleksii
created: 2026-06-12T20:00:00Z
start_date: 2026-06-12T20:00:00Z
finish_date: 2026-06-12T22:00:00Z
updated: 2026-06-12T22:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-130]
commits: [87ca6ee]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-146 — TODAY / LAST TIME recap headers not on same baseline

## Problem
In the `<ComparisonRecap>` header row, `TODAY` (flush-left) and `LAST TIME`
(flush-right) were placed using the 4-column data grid (`items-center`). The
grid had empty `<span />` spacers in the set-number and delta columns; the
two text spans were in columns 2 and 4. Despite `items-center`, differences
in rendered column heights and the gap between them created a visual baseline
misalignment on device.

## Fix
Replace the 4-column grid header with a simple `flex items-baseline justify-between`
row. TODAY is `<span>` (natural left), LAST TIME is `<span>` (natural right,
no text-right needed since flex justify-between handles it). Both are on one
shared text baseline, independent of the underlying data grid columns.

## Files changed
- `apps/web/src/components/record/ComparisonRecap.tsx` — header row changed
  from GRID-based `<div>` with 4 spans to `flex items-baseline justify-between`

## Acceptance
- [x] TODAY and LAST TIME visually on the same baseline in dark mode (screenshot: iphone15pro-3-gym146-recap-headers.png)
- [x] Alignment correct at 375px and 393px widths (Y-diff 0.0px at both viewports)

## Comments

### 2026-06-12T22:00:00Z — done
Playwright measured Y-diff = 0.0px at both 393x852 and 375x667.
Screenshot shows "Today" flush-left and "Last time" flush-right on same row. Commit 87ca6ee.
