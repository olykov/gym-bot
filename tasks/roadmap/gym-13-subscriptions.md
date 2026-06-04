---
schema_version: 1
id: GYM-13
title: "Phase 6: Free/paid subscriptions + entitlements"
slug: gym-13-subscriptions
status: backlog
priority: medium
type: feature
labels: [phase-6, billing]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-13 — Phase 6: Free/paid subscriptions + entitlements

## Problem
No subscription/entitlement model to gate premium features.

## Plan
subscriptions/entitlements domain in apps/api; tier middleware; payment provider (Telegram Stars and/or Stripe) behind the API.

## Comments

### 2026-05-31T16:00:00Z — task created
Gates AI/advanced analytics/calorie tracker uniformly.

### 2026-06-04 — sequencing: do AFTER the admin foundation
Operator decision (2026-06-04): entitlements/limits/trials are SET by the operator, and there is
nowhere to set them until the admin panel is rebuilt/relocated (it currently lives in apps/admin,
degraded after the Phase 5 cutover). So GYM-13 is blocked on the admin-foundation work — build that
first, then GYM-13. The entitlements rows are user-owned → reuse the RLS `enable_user_rls` convention
([[gymbot-rls-architecture]]); admin writes them via admin-JWT routes.
