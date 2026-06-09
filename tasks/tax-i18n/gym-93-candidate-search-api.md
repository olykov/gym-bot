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
depends_on: [GYM-108]
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

## Scope (layers): contract + API. Per ADR 0003 (Channel B).
- New `GET /exercises/search?q=&muscle_id=&lang=&limit=` → ranked canonical candidates matched by
  name_key exact → prefix → `exercise_alias` hit (lang-aware) → `pg_trgm` fuzzy (typos). Return
  canonical exercise id, display name, muscle. Muscle-scoped when called from within a muscle, else
  whole catalog. `lang` comes from GYM-108 (Telegram language_code).
- Requires `CREATE EXTENSION IF NOT EXISTS pg_trgm` — migration `0007` (auto-applies on deploy via GYM-107).
- DECOUPLED from the seed: works over the 122 English canonical names with ZERO aliases; GYM-92 enriches.
- No embeddings here (that is GYM-96, the AI phase). pg_trgm only.

## Acceptance
- [ ] Search returns ranked canonical candidates (key/alias/fuzzy) with i18n names; muscle filter works;
      tests + suite green.
