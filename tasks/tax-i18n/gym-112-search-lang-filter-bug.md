---
schema_version: 1
id: GYM-112
title: "Bug: exercise search alias tier hard-filters by UI lang, so RU aliases miss when UI locale is en"
slug: gym-112-search-lang-filter-bug
status: in_progress
priority: high
type: bug-fix
labels: [api, i18n, search, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T04:00:00Z
start_date: 2026-06-10T04:00:00Z
finish_date: null
updated: 2026-06-10T04:00:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-92, GYM-93]
commits: []
tests: []
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
- [ ] `Жим…` with `lang='en'` (or any lang) resolves to Barbell Bench Press via the alias tier.
- [ ] English search unaffected; muscle scoping unaffected; suite green (add a regression test: RU query +
      `lang='en'` still matches).

## Comments

### 2026-06-10T04:00:00Z — start
Found live by operator. Root cause = the alias-tier `a.lang = :lang` filter. Delegated fix to core-api.
