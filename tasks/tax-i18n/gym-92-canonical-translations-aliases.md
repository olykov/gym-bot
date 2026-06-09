---
schema_version: 1
id: GYM-92
title: "Content/DB: canonical EXERCISE translations + aliases seed (RU first) — muscles moved to GYM-109"
slug: gym-92-canonical-translations-aliases
status: backlog
priority: medium
type: feature
labels: [taxonomy, db, content, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-i18n
depends_on: [GYM-108]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-92 — i18n catalog content

## Problem
To let users pick canonical names from a list in their language (and to resolve "Жим лёжа" → Bench Press),
we need translations + aliases for the canonical catalog. Per ADR 0001.

## Scope: content + DB seed (Channel B, ADR 0003). EXERCISES ONLY — muscles localize in GYM-109.
- Prepare RU translations for the 122 canonical exercises (+ common synonyms/abbreviations). EN aliases
  unnecessary (canonical name is already English + searchable via name_key).
- Generation: AI-drafted RU table (`canonical → RU`) → operator review → seed.
- Seed into `exercise_alias.lang='ru'` via migration `0007` (idempotent, `ON CONFLICT DO NOTHING`),
  auto-applied on deploy (GYM-107).
- Enrichment only — does NOT block GYM-93 search (which works over English names).

## Acceptance
- [ ] Canonical exercises/muscles have translations + seeded aliases for the initial language set; seeding
      is idempotent and re-runnable.
