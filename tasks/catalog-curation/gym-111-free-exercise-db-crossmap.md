---
schema_version: 1
id: GYM-111
title: "Cross-map KEEP exercises to free-exercise-db (authoritative names + equipment + muscle)"
slug: gym-111-free-exercise-db-crossmap
status: done
priority: high
type: research
labels: [catalog, content, data]
assignee: null
model: claude-opus-4-8
reporter: oleksii
created: 2026-06-10T02:00:00Z
start_date: 2026-06-10T02:00:00Z
finish_date: 2026-06-10T03:00:00Z
updated: 2026-06-10T03:00:00Z
epic: catalog-curation
depends_on: []
blocks: [GYM-110]
related: [GYM-92]
commits: [55e3442]
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

### 2026-06-10 — crossmap artifact produced
Dataset: https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json
(free-exercise-db, yuhonas, public domain / Unlicense) — 873 entries.
Matched all 97 KEEP rows with a token-set + difflib seq-ratio scorer (weighted 0.7/0.3) in
`/tmp/crossmap.py`. Confidence buckets: high >=0.62, med >=0.45, low >=0.30, none <0.30.

Confidence histogram (97 KEEP rows): **high=68, med=19, low=10, none=0**.

The 10 low-confidence rows are best-effort matches where free-exercise-db has no close analog
(machine-specific names: Pec Deck, Belt Squat, Iso-Lateral Low Row, Cable/Machine Pullover,
Chest-Supported Row, Hip Abduction, 45-Degree Hyperextension, Neutral-Grip Seated Row, Back Extension).
These need operator verification before GYM-110 applies equipment/muscle from fxdb.

Artifact (uncommitted working file): `packages/db/seeds/fxdb_crossmap.tsv`. Names-only proposals;
`canonical_curation.tsv` was NOT modified.

### 2026-06-10T03:00:00Z — done (artifact versioned with GYM-110)
The cross-map artifact `packages/db/seeds/fxdb_crossmap.tsv` is now committed alongside the GYM-110
curation migration (it anchored the KEEP canonical names). Versioned in commit 55e3442 on branch
`catalog/gym-110-apply`. Closing as done; GYM-110 consumed the proposals.
