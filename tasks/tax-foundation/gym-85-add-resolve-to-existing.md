---
schema_version: 1
id: GYM-85
title: "Add resolves-to-existing (silent unhide) + dedup on create & rename within visible set"
slug: gym-85-add-resolve-to-existing
status: in_progress
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T13:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-foundation
depends_on: [GYM-84]
blocks: []
related: [GYM-86]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-85 — Resolve-to-existing + dedup

## Problem
Adding/renaming should be smart about existing names (incl. hidden ones), per ADR 0001.

## Scope (layers): contract + API + frontend (split into waves at execution)
- API add flow: normalize → look up by name_key in the caller's VISIBLE set →
  - match found & visible → return it (no dup);
  - match found but HIDDEN → **silently unhide** and return it (no prompt — operator decision);
  - no match → create the custom as today.
- Dedup-on-create: typing a name whose key matches one you ALREADY have visible → 409 "you already have
  this exercise/muscle".
- Dedup-on-rename: renaming (own custom OR a canonical alias) to a key that collides with another item in
  your visible set → 409, same message.
- Frontend: surface the unhide-and-select silently; show a graceful inline dedup message on the explicit
  collision cases.

## Key decisions (operator)
- Same-name-as-a-hidden-item → unhide silently, do not ask.
- Different-string with no alias link (e.g. "жим лёжа" while Bench Press hidden) → just create the custom;
  do nothing clever (matching is a later phase).

## Acceptance
- [ ] Re-adding a hidden item unhides it silently; adding/renaming to an existing visible name → 409 with a
      clear message; a genuinely new name still creates; covered by tests; build/suite green.
