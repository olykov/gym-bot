---
schema_version: 1
id: GYM-141
title: "History: PR shown on the day but no marker on the actual set inside the day"
slug: gym-141-pr-marker-on-set
status: in_progress
priority: high
type: bug-fix
labels: [frontend,design,history,feature]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: null
updated: 2026-06-12T08:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-141 — History: PR shown on the day but no marker on the actual set inside the day

## Problem (operator, on-device review of the Fable batch)
- The day shows a PR badge (has_pr, GYM-136) but inside the day there is NO indication of WHICH
  set/exercise is the PR — the operator sees "PR", opens the day, and can't find what/where it was.
  Add a clear PR marker on the specific set (and/or exercise group) that holds the day's record. Derive
  client-side if the data allows (day sets + the exercise's standing max); if it needs an API/contract
  per-set flag, STOP and flag it (then it goes to core-api). ultrathink + frontend-design plugin.
