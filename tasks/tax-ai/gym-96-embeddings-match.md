---
schema_version: 1
id: GYM-96
title: "DB+worker: pgvector embeddings over canonical+aliases; nearest-neighbor match scoring"
slug: gym-96-embeddings-match
status: backlog
priority: low
type: feature
labels: [taxonomy, db, ai]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-08T08:00:00Z
epic: tax-ai
depends_on: [GYM-87, GYM-95]
blocks: [GYM-97]
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-96 — Embedding match

## Problem
Catch synonyms/translations not in the alias table ("жим лёж" → Bench Press) with a confidence score.
Per ADR 0001 (AI phase, LAST; embeddings before LLM).

## Scope (layers): DB + worker
- pgvector over canonical names + aliases. The worker embeds an unmatched custom name and finds the nearest
  canonical with a confidence score. Threshold → candidate suggestion (never a silent bind). LLM classify
  reserved only for the ambiguous tail / offline alias bootstrapping.

## Acceptance
- [ ] Worker produces scored canonical candidates for an unmatched custom name via embeddings; results are
      suggestions only; tests green.
