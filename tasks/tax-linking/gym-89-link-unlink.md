---
schema_version: 1
id: GYM-89
title: "Link/Unlink: link a custom exercise to a canonical (same-muscle, pick-from-list, highlight linked)"
slug: gym-89-link-unlink
status: backlog
priority: high
type: feature
labels: [taxonomy, api, api-contract, frontend, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-linking
depends_on: [GYM-86, GYM-87]
blocks: []
related: [GYM-90]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-89 — Link / Unlink

## Problem
A user with a custom "жим лёжа" wants to join ratings → must link it to canonical Bench Press. Per ADR 0001
(manual link first; AI later).

## Scope (layers): contract + API + frontend
- API: link(user_exercise → canonical_id) and unlink. Validation: the canonical MUST be in the SAME muscle
  as the user exercise (no cross-muscle links). Own exercise only.
- Frontend (design plugin): a Link action (placement TBD in design — manage sheet candidate). Tapping it
  shows a list of CANONICAL exercises **filtered to the exercise's muscle** — pick one, **no free-add**
  (selection only). Highlight already-linked exercises in the picker (visual marker). Provide Unlink.
- Edge: if the exercise is in the wrong muscle, the user must first MOVE it (GYM-90) to reach the right
  canonical list.

## Key decisions (operator)
- Link list = canonical only, same muscle, no add. Linked exercises are highlighted. Unlink available.

## Acceptance
- [ ] Link a custom to a same-muscle canonical (no cross-muscle, no free-add); unlink; linked exercises
      highlighted; tests + build green.
