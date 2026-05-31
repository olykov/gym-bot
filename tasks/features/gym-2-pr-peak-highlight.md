---
schema_version: 1
id: GYM-2
title: "Highlight PR weight and max-reps buttons in green"
slug: gym-2-pr-peak-highlight
status: done
priority: medium
type: feature
labels: [features, ui]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T09:03:35Z
start_date: 2026-05-31T09:03:35Z
finish_date: 2026-05-31T09:03:35Z
updated: 2026-05-31T09:03:35Z
epic: features
depends_on: []
blocks: []
related: []
commits: ["85809ba"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-2 — Highlight PR weight and max-reps buttons in green

## Problem
No visual cue for the user's personal-record weight or max reps at a given weight.

## Solution
Added get_max_reps_for_weight; green SUCCESS style on the PR-weight and max-reps buttons; float-based matching; callback_data unchanged.

## Comments

### 2026-05-31T09:03:35Z — migrated
Verified live by operator.
