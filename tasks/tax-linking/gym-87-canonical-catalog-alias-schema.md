---
schema_version: 1
id: GYM-87
title: "DB: canonical catalog formalization + alias/synonym table + merge-support columns"
slug: gym-87-canonical-catalog-alias-schema
status: in_progress
priority: high
type: feature
labels: [taxonomy, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T20:30:00Z
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-linking
depends_on: [GYM-84]
blocks: [GYM-88, GYM-89, GYM-92, GYM-93]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-87 — Canonical catalog + alias schema

## Problem
Linking, i18n dropdowns, and AI matching all need a formal canonical catalog + an alias/synonym store.
Per ADR 0001.

## Scope (layers): DB (Alembic)
- Formalize the canonical exercise/muscle catalog (stable ids, canonical name, muscle, equipment/variation
  fields as needed — keep grain "movement + equipment"; parent/variation later, YAGNI now).
- Add an `exercise_alias` table: (canonical_id, alias_name, name_key, lang) — many aliases per canonical,
  incl. translations. Index by name_key for fast resolve. (Muscle aliases too if needed.)
- Reserve merge-support: ensure canonical ids are stable and design so a merge can repoint references and
  leave a redirect alias (the operation itself is GYM-88).

## Acceptance
- [ ] Canonical catalog + exercise_alias table in schema with name_key index; migration applies; ready for
      seeding (GYM-92), linking (GYM-89), and merge (GYM-88).
