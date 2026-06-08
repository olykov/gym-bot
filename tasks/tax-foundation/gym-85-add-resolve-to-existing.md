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
commits: [013d658]
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

## Comments

### 2026-06-08 — Contract slice (commit 013d658)

Done in `packages/api-contract/openapi.yaml` only (CONTRACT slice; API/frontend follow).

- Added optional `resolution` to both `Muscle` and `Exercise` read schemas — string enum
  `[created, unhidden, existing]`, `type: ['string', 'null']`, NOT required (modeled like
  `is_mine`). Stays absent/null on list/read responses → non-breaking for bot/admin clients.
  Desc: 'created' = new row; 'unhidden' = an existing hidden item was silently unhidden;
  'existing' = item already existed and visible (no duplicate created).
- Documented find-or-create-or-unhide on `POST /muscles` and `POST /exercises` (user by-name):
  name normalized to key; if a row with that key exists in the caller's scope → hidden is
  silently unhidden (resolution=unhidden, HTTP 200), visible is returned as-is with no duplicate
  (resolution=existing, HTTP 200); otherwise a new row is created (resolution=created, HTTP 201).
  Both endpoints now document the 200 (resolved) and 201 (created) responses. Request bodies
  unchanged.
- Rename PATCH contract untouched (409-on-duplicate already exists; GYM-85 rename dedup is an
  API-internal key-based comparison, no contract change).
- `make validate` passes (OpenAPI 3.1, 34 paths, 38 schemas). Regenerated both clients
  (`make gen-python`, `make gen-typescript`). Python `models.py` imports cleanly: `Resolution`
  enum = [created, unhidden, existing]; `resolution` present on `Muscle` and `Exercise`.
  TS `tsc --noEmit --strict` passes; `resolution?: "created" | "unhidden" | "existing" | null`
  present on both. Note: TS client is gitignored (regenerated on demand), Python client is the
  installable tracked artifact.
