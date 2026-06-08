---
schema_version: 1
id: GYM-93
title: "API: candidate search over canonical names + aliases (name_key + synonym + pg_trgm fuzzy), muscle-scoped"
slug: gym-93-candidate-search-api
status: backlog
priority: medium
type: feature
labels: [taxonomy, api, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-i18n
depends_on: [GYM-87, GYM-92]
blocks: [GYM-94]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-93 — Candidate search endpoint

## Problem
The add-exercise dropdown needs ranked canonical candidates as the user types. Per ADR 0001 (cheap layers
before AI).

## Scope (layers): contract + API
- Search endpoint: input a query (and optionally a muscle) → ranked canonical candidates matched by
  name_key exact → alias hit → pg_trgm fuzzy (typos). Return canonical_id, display name in the user's
  language, muscle. Muscle-scoped when called from within a muscle.
- No embeddings here (that is GYM-96, the AI phase). pg_trgm only.

## Acceptance
- [ ] Search returns ranked canonical candidates (key/alias/fuzzy) with i18n names; muscle filter works;
      tests + suite green.
