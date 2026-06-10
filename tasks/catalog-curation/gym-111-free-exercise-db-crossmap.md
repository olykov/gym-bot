---
schema_version: 1
id: GYM-111
title: "Cross-map KEEP exercises to free-exercise-db (authoritative names + equipment + muscle)"
slug: gym-111-free-exercise-db-crossmap
status: in_progress
priority: high
type: research
labels: [catalog, content, data]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T02:00:00Z
start_date: 2026-06-10T02:00:00Z
finish_date: null
updated: 2026-06-10T02:00:00Z
epic: catalog-curation
depends_on: []
blocks: [GYM-110]
related: [GYM-92]
commits: []
tests: []
design_reports: ["docs/adr/0004-canonical-catalog-governance.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-111 — Cross-map KEEP exercises to free-exercise-db

## Problem
Per ADR 0004, KEEP (public canonical) names should be anchored to an authoritative open dataset rather than
freehand. free-exercise-db (yuhonas, public domain, ~800 exercises) provides standard names + equipment +
muscles.

## Solution
For each KEEP row in `packages/db/seeds/canonical_curation.tsv`, find the best-matching free-exercise-db
entry; propose its authoritative name + equipment + primary muscle. Flag low-confidence / no-match for the
operator. Output a review column; do NOT change actions (KEEP/DEMOTE/MERGE) — names only.

## Comments

### 2026-06-10T02:00:00Z — start
Delegated to a research agent (background): fetch the dataset, fuzzy-match the ~97 KEEP rows, produce a
mapping for operator review. Feeds GYM-110 (apply) and later GYM-92 (RU from wger on the clean set).
