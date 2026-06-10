---
schema_version: 1
id: GYM-113
title: "Search: add substring (contains) matching so a query word anywhere in the name/alias matches"
slug: gym-113-search-substring-matching
status: in_progress
priority: high
type: feature
labels: [api, search, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T05:00:00Z
start_date: 2026-06-10T05:00:00Z
finish_date: null
updated: 2026-06-10T05:00:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-93, GYM-112]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-113 — Search substring (contains) matching

## Problem
`GET /exercises/search` matches names by exact -> PREFIX -> fuzzy. A query that is a word in the MIDDLE/END
of the name doesn't prefix-match, so it only weakly fuzzy-matches. Live: "Press" returns just 1 result
(Barbell Bench Press, fuzzy) and misses "Cable Chest Press", "Dumbbell Bench Press", etc. — even though
they all contain "Press". Russian "Жим" works only because the RU aliases START with «Жим» (prefix). The
catalog search lacks substring recall.

## Solution
Add a CONTAINS tier (`name_key LIKE '%' || q || '%'`) on both `exercises.name_key` and
`exercise_alias.name_key`, ranked between prefix and fuzzy. Make matching symmetric across languages: any
query that is a substring of a name (or alias) returns that exercise. Keep the existing enum
(`exact|prefix|alias|fuzzy`) — label name-substring hits `prefix` (a clean direct name match → silent badge,
same UX as prefix) and alias-substring hits `alias` (`aka`). No contract change.

## Acceptance
- [ ] "Press" returns all press exercises in the muscle (Barbell Bench Press, Cable/Decline/... Chest Press,
      Dumbbell Bench Press), symmetric with "Жим".
- [ ] Exact/prefix still rank above contains; fuzzy still last; muscle scoping + dedup-by-id intact.
- [ ] Suite green with a regression test for the "Press" case.

## Comments

### 2026-06-10T05:00:00Z — start
Found live by operator (screenshots: "Press" -> 1 result vs "Жим" -> 4+). Root cause = prefix-only name
matching, no substring tier. Delegated to core-api.
