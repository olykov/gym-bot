---
schema_version: 1
id: GYM-91
title: "Decision: canonical muscle-placement override policy (per-user re-placement vs edit canonical)"
slug: gym-91-canonical-placement-policy
status: backlog
priority: medium
type: research
labels: [taxonomy, decision, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-moves
depends_on: [GYM-87]
blocks: []
related: [GYM-90]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-91 — Canonical placement override policy (decision)

## Problem
Users may disagree with canonical muscle placement (e.g. "Brachioradialis Barbell Curl" sits in Biceps but
arguably belongs in Forearms). Do we allow per-user re-placement of a canonical, edit the canonical for
everyone (admin), or both? Per ADR 0001 (placement is overridable; mechanism TBD).

## Scope: research / ADR addendum
- Options: (a) per-user placement override (the override row from GYM-86 carries muscle); (b) admin-only
  canonical re-placement; (c) both. Weigh impact on linking (GYM-89 same-muscle scope), ratings, and AI
  muscle-balance. Recommend, then record as an ADR addendum and spawn the build task.

## Acceptance
- [ ] Decision recorded (ADR addendum) with the chosen mechanism + follow-up build task created.
