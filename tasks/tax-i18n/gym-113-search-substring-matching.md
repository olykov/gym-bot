---
schema_version: 1
id: GYM-113
title: "Search: add substring (contains) matching so a query word anywhere in the name/alias matches"
slug: gym-113-search-substring-matching
status: done
priority: high
type: feature
labels: [api, search, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T05:00:00Z
start_date: 2026-06-10T05:00:00Z
finish_date: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-93, GYM-112]
commits: [af5f60a]
tests: [apps/api/tests/test_gym113_search_substring.py]
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
- [x] "Press" returns all press exercises in the muscle (Barbell Bench Press, Cable/Decline/... Chest Press,
      Dumbbell Bench Press), symmetric with "Жим".
- [x] Exact/prefix still rank above contains; fuzzy still last; muscle scoping + dedup-by-id intact.
- [x] Suite green with a regression test for the "Press" case.

## Comments

### 2026-06-10T05:00:00Z — start
Found live by operator (screenshots: "Press" -> 1 result vs "Жим" -> 4+). Root cause = prefix-only name
matching, no substring tier. Delegated to core-api.

### 2026-06-10 — done (af5f60a)
Added tier 3 (contains) to _SEARCH_SQL in apps/api/app/api/v1/exercises_router.py:
- name_key LIKE '%' || q_key.k || '%', score 0.5, match_reason='prefix', tier=3.
  Excludes rows already matched by exact (tier 1) or prefix (tier 2).
- Alias tier extended from (exact OR prefix) to full substring: a.name_key LIKE '%' || q_key.k || '%'.
- Tier rank integers: exact=1, prefix=2, contains=3, alias=4, fuzzy=5 (DISTINCT ON dedup keeps best).
- Final ORDER BY uses match_reason case (exact=1,prefix=2,alias=3,fuzzy=4) + score DESC + name;
  contains hits surface as match_reason='prefix' score=0.5, naturally after real prefix hits (0.8).
- Contract unchanged: enum stays exact|prefix|alias|fuzzy.
- 430/430 tests pass (9 new in test_gym113_search_substring.py).
