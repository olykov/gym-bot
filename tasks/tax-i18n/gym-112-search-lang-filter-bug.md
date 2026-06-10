---
schema_version: 1
id: GYM-112
title: "Bug: exercise search alias tier hard-filters by UI lang, so RU aliases miss when UI locale is en"
slug: gym-112-search-lang-filter-bug
status: done
priority: high
type: bug-fix
labels: [api, i18n, search, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T04:00:00Z
start_date: 2026-06-10T04:00:00Z
finish_date: 2026-06-10
updated: 2026-06-10T10:00:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-92, GYM-93]
commits: [GYM-112-fix]
tests: [tests/test_gym112_search_lang_filter_bug.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-112 — Search alias tier hard-filters by UI lang

## Problem
`GET /exercises/search` alias tier (GYM-93) filters `AND (:lang IS NULL OR a.lang = :lang)`. The frontend
(GYM-94) passes `lang` from the resolved UI locale (GYM-108 / Telegram `language_code`). When the operator's
Telegram is English, `lang='en'`, so the RU aliases (`lang='ru'`, seeded GYM-92) are EXCLUDED — a Russian
query ("Жим…") returns nothing, even though the alias exists. English queries work (they hit the
`exercises.name` tiers, which are not lang-filtered). Confirmed live: same exercise (Barbell Bench Press)
is found by "Barb" but not by "Жим".

## Solution
Aliases are alternate names a user may type in ANY language — matching must NOT be gated by the UI locale.
Remove the `lang` condition from the alias tier so it matches by `name_key` regardless of `a.lang`. Keep the
`lang` query param in the contract (backward-compatible; reserved for future ranking/display), but it no
longer filters matches. Muscle scoping unchanged.

## Acceptance
- [x] `Жим…` with `lang='en'` (or any lang) resolves to Barbell Bench Press via the alias tier.
- [x] English search unaffected; muscle scoping unaffected; suite green (add a regression test: RU query +
      `lang='en'` still matches).

## Comments

### 2026-06-10T04:00:00Z — start
Found live by operator. Root cause = the alias-tier `a.lang = :lang` filter. Delegated fix to core-api.

### 2026-06-10T10:00:00Z — done
Removed `AND (CAST(:lang AS text) IS NULL OR a.lang = CAST(:lang AS text))` from Tier 3 of `_SEARCH_SQL`
in `apps/api/app/api/v1/exercises_router.py`. The `lang` query param is kept in the function signature for
backward compatibility (reserved for future ranking/display) but is no longer passed to the SQL.
Note: SQL inline comments must not use `:param` syntax — SQLAlchemy parses them as bind parameters.
Regression test added: `tests/test_gym112_search_lang_filter_bug.py` (5 tests). Full suite: 421 passed, 0 failed.
