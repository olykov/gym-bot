---
schema_version: 1
id: GYM-1
title: "aiogram 3.28 upgrade + colored inline buttons"
slug: gym-1-aiogram-upgrade-colored-buttons
status: done
priority: high
type: feature
labels: [features, ui]
assignee: null
model: null
reporter: oleksii
created: 2026-05-30T21:25:43Z
start_date: 2026-05-30T21:25:43Z
finish_date: 2026-05-31T07:36:33Z
updated: 2026-05-31T07:36:33Z
epic: features
depends_on: []
blocks: []
related: []
commits: ["e5fbfb1", "1228d1e"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-1 — aiogram 3.28 upgrade + colored inline buttons

## Problem
Bot inline buttons were all neutral; Bot API 9.4 button colors needed aiogram>=3.28.

## Solution
Upgraded aiogram 3.18->3.28.2; applied ButtonStyle (success/primary/danger) across markups; semantic color map.

## Comments

### 2026-05-31T07:36:33Z — migrated
Shipped and deployed. Colors render on API 9.4+ clients.
