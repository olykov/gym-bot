---
schema_version: 1
id: GYM-30
title: "Hotfix: client models rejected naive datetimes from the API"
slug: gym-30-client-naive-datetime
status: done
priority: high
type: bug-fix
labels: [phase-3, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T14:15:00Z
start_date: 2026-06-01T14:15:00Z
finish_date: 2026-06-01T14:20:00Z
updated: 2026-06-01T14:20:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-27, GYM-10]
commits: ["5bc4da2"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-30 — Hotfix: client models rejected naive datetimes from the API

## Problem
The generated Python client models (datamodel-code-generator default for pydantic v2) typed every
date-time field as `AwareDatetime`, but the API serializes NAIVE datetimes (the DB `training.date`
and `users.registration_date`/`last_interaction` columns are `TIMESTAMP` without tz). Any client
response carrying a date — PersonalRecord, TrainingHistoryEntry, Training, User — raised a pydantic
`ValidationError` ("Input should have timezone info"). Caught by the prod smoke (the local e2e used
raw curl, which did not exercise the client's model validation, so it missed this).

## Solution
Changed the client models to plain `datetime` (accepts both naive and aware) and pinned
`--output-datetime-class datetime` in packages/api-contract/Makefile so regeneration stays consistent.
Deployed; re-smoked in prod via the bot's own client: list_muscles, get_personal_record (date parsed),
get_training_history all succeed.

## Comments

### 2026-06-01T14:20:00Z — done
Found during the Phase 3 prod smoke (the bot's real client hitting prod). Fixed in 5bc4da2, redeployed
(run 26760579227 success), re-verified. The tz-awareness of stored timestamps (the bot historically
wrote naive local time) is a separate data-quality concern, not changed here.
