---
schema_version: 1
id: GYM-97
title: "API+frontend: surface AI match SUGGESTIONS with user confirm (never silent bind) for unmatched customs"
slug: gym-97-suggest-confirm-ui
status: backlog
priority: low
type: feature
labels: [taxonomy, api, frontend, ai, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-ai
depends_on: [GYM-96]
blocks: []
related: [GYM-89]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-97 — Suggest + confirm

## Problem
Turn AI candidates into a safe, user-confirmed link. Per ADR 0001 (AI suggests, human confirms — never
silent bind, which would pollute shared leaderboards).

## Scope (layers): API + frontend (design plugin)
- Surface "we think '<custom>' might be Bench Press — link?" with one-tap confirm/dismiss. On confirm →
  reuse the GYM-89 link. Never auto-link silently. Dismiss is sticky (don't nag).

## Acceptance
- [ ] Unmatched customs get an optional, confirmable link suggestion; confirm links via GYM-89; no silent
      binding; design consistent; build green.
