---
schema_version: 1
id: GYM-86
title: "DB+API+frontend: per-user exercise override (canonical_id + display_name) — rename a canonical keeps the link"
slug: gym-86-canonical-reference-overrides
status: in_progress
priority: high
type: feature
labels: [taxonomy, db, api, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T20:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-foundation
depends_on: [GYM-84]
blocks: [GYM-89]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-86 — Reference + overrides

## Problem
A user should be able to rename a CANONICAL exercise to their own name while the canonical link persists
(so ratings/PRs still aggregate). Today rename only works on a user's OWN custom row. Per ADR 0001.

## Scope (layers): DB + API + frontend
- DB: introduce the per-user override seam — either a `user_exercise` row referencing `canonical_id` with
  a `display_name` override (+ hidden/sort), or equivalent columns. Same for muscles if we want canonical
  muscle aliases (decide; muscles are a small stable taxonomy). Migration + RLS (user-owned override rows).
- API: renaming a canonical creates/updates the caller's override (alias) rather than mutating the shared
  row; reads return the effective display_name but keep canonical_id; hide/move/etc. operate on the override.
- Frontend: rename of a canonical now allowed (produces an alias); the tile shows the user's name; manage
  sheet reflects the link. Shared surfaces must still use the canonical name (note for later).

## Key decisions (operator)
- Display = user's alias; identity = canonical_id (preserved).

## Acceptance
- [ ] Renaming a canonical exercise stores a per-user alias with canonical_id intact; personal views show
      the alias; canonical identity unchanged for everyone else; tests + build/suite green.
