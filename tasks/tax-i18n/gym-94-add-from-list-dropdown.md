---
schema_version: 1
id: GYM-94
title: "Frontend: add-exercise = search-and-pick dropdown (suggestions first; free-text create-as-is last resort)"
slug: gym-94-add-from-list-dropdown
status: backlog
priority: medium
type: feature
labels: [taxonomy, frontend, design, ux, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-i18n
depends_on: [GYM-93]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-94 — Add-from-list dropdown

## Problem
Today add-exercise is free text → fragmentation. Make it a search-and-pick over the canonical catalog so
users mostly choose prepared names. Per ADR 0001.

## Scope (layers): frontend (design plugin)
- As the user types, show ranked canonical suggestions (GYM-93) in the muscle. Picking one creates/links to
  the canonical (with the user's language name). 
- Free-text "create '<typed>' as a new exercise" is offered ONLY as the last resort, after suggestions, when
  nothing fits. This trains users onto canonical names.
- Keep Chalk & Iron; reuse the picker/manage-sheet language; mobile-first.

## Key decisions (operator)
- Suggestions first; free-text create only if nothing in the list fits.

## Acceptance
- [ ] Add-exercise shows canonical suggestions as you type; pick = canonical/link; free-text create is the
      last-resort fallback; design consistent; build green.
