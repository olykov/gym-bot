---
schema_version: 1
id: GYM-95
title: "Infra: async queue + worker seam (background jobs) — foundation for AI suggestions"
slug: gym-95-queue-worker-seam
status: backlog
priority: low
type: chore
labels: [taxonomy, infra, ai]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-ai
depends_on: []
blocks: [GYM-96, GYM-97]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-95 — Queue + worker seam

## Problem
AI match suggestions run async (operator's queue+worker idea). Need a background job seam. Per ADR 0001
(AI phase, LAST).

## Scope (layers): infra + API
- A queue (Redis-backed is already in the stack) + a worker process that pulls jobs. Keep it minimal and
  generic (reusable for other future async work). Deploy wiring (compose/CI).

## Acceptance
- [ ] A worker consumes enqueued jobs reliably; documented; deployable. (No AI logic yet.)
