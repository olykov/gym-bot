---
schema_version: 1
id: GYM-92
title: "Content/DB: canonical exercises + muscles translations in N languages + per-language aliases (seed)"
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
depends_on: [GYM-87]
blocks: [GYM-93]
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

## Scope: content + DB seed
- Prepare translations for canonical exercises + muscles in the target languages (start RU/EN; extend).
- Seed per-language aliases into `exercise_alias` (GYM-87): common names, translations, abbreviations.
- A repeatable seeding script (idempotent) so the catalog can grow.

## Acceptance
- [ ] Canonical exercises/muscles have translations + seeded aliases for the initial language set; seeding
      is idempotent and re-runnable.
