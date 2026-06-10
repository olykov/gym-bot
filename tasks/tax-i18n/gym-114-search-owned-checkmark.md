---
schema_version: 1
id: GYM-114
title: "Search UX: drop match-reason badge; show a check + dimmed text for exercises already in the user's list"
slug: gym-114-search-owned-checkmark
status: in_progress
priority: high
type: feature
labels: [frontend, design, ux, search, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T05:30:00Z
start_date: 2026-06-10T05:30:00Z
finish_date: null
updated: 2026-06-10T05:30:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-94, GYM-113]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-114 — Search results: owned-checkmark instead of match-reason badge

## Problem
The add-exercise search dropdown (GYM-94, `ExerciseSearchField`) shows a right-side badge per candidate —
`aka` (alias) / `~` (fuzzy). The operator finds the badge noise. More useful: show which candidates the
user ALREADY HAS in the current muscle's list (so they see at a glance what's new vs already added).

## Solution (frontend-only if feasible)
- REMOVE the `match_reason` badge (`aka` / `~`) from every search result.
- For each candidate that is ALREADY in the user's exercise list for the selected muscle, show a
  **checkmark (✓)** on the right and render its name in a **dimmed / gray** color (uses a hint/muted token).
  New candidates (not yet in the list) render normally.
- "Create «…»" stays the last row. Picking an already-owned candidate behaves as today (selects it).
- Determine "already in the user's list" from data the picker already has (the muscle's exercise list that
  RecordPicker loaded). Match search candidates by exercise `id`. Consider HIDDEN exercises too (an exercise
  the user hid is still "theirs") — if the hidden set isn't readily available client-side, implement for the
  visible list and note the gap (do not add a backend/contract change without flagging it first).

## Acceptance
- [ ] No `aka`/`~` badges in search results.
- [ ] Candidates already in the muscle's list show a ✓ + dimmed name; new ones render normally.
- [ ] Record flow unchanged; design tokens only; build + typecheck green; frontend-design plugin used.

## Comments

### 2026-06-10T05:30:00Z — start
Operator request (post search-quality fixes GYM-112/113). Delegated to frontend-design-engineer.
