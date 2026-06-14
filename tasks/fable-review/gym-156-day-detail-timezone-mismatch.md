---
schema_version: 1
id: GYM-156
title: "Day detail empty though the list shows sets: detail uses UTC day bounds, list groups by tz"
slug: gym-156-day-detail-timezone-mismatch
status: done
priority: high
type: bug-fix
labels: [api, core-api, frontend, api-contract, history, timezone, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T20:10:00Z
updated: 2026-06-14T04:05:00Z
start_date: 2026-06-13T20:10:00Z
finish_date: 2026-06-14T04:05:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [c7d712f]
tests: [apps/api/tests/test_gym156_day_detail_tz.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-156 — Day detail EMPTY while the day card shows sets (tz boundary mismatch)

## Problem (operator, confirmed in prod DB)
History list shows "FRI 05 JUN — Shoulders — 1 exercise · 2 sets", but opening that day
shows "EMPTY DAY". The two Shoulders (Face Pull) sets are stored at
`2026-06-04 20:02 UTC` = `2026-06-05 00:02` Asia/Tbilisi (logged at 00:02 local on Jun 5).

## Root cause
- `GET /training/days` (`list_training_days`) groups by
  `(date AT TIME ZONE 'UTC' AT TIME ZONE :tz)::date` → buckets the set into the LOCAL date
  (Jun 5). The frontend (`useTrainingDays`) passes `DEVICE_TZ`.
- `GET /training/day/{date}` (`get_training_day`) has NO tz param and computes
  `dt_from = datetime(y,m,d)` / `dt_to = +1 day` → a UTC day window
  `[Jun 5 00:00 UTC, Jun 6 00:00 UTC)`. The sets at Jun 4 20:02 UTC are NOT in that range →
  empty. The frontend (`useTrainingDay`/`getTrainingDay`) doesn't pass tz either.

So sets logged near local midnight land on different days between the two endpoints.

## Fix (mirror the existing list-endpoint tz handling)
1. **api-contract**: add an optional `tz` query param (IANA name) to `GET /training/day/{date}`
   (additive, non-breaking). Regen clients.
2. **core-api**: accept `tz`; when present, compute the day window as the UTC instants of the
   LOCAL midnight boundaries of `day_date` in `tz` (zoneinfo): `dt_from = local_midnight(tz)→UTC`,
   `dt_to = next_local_midnight(tz)→UTC`. Keep the WHERE on the raw `date` column (sargable),
   exactly like the list endpoint's intent. No tz → current UTC behaviour (back-compat).
   For Jun 5 / Tbilisi (UTC+4): window = [Jun 4 20:00 UTC, Jun 5 20:00 UTC) → the 20:02 sets are
   included. Tests incl. the near-midnight cross-day case + a DST-offset tz.
3. **frontend**: `getTrainingDay(date, tz)` + `useTrainingDay` passes `DEVICE_TZ` and keys on it
   (mirror `useTrainingDays`), so the detail matches what the list bucketed.

## Validation
Against prod data: opening Jun 5 (tz Asia/Tbilisi) must return the 2 Face Pull sets that the
list counts under Jun 5; opening Jun 4 must NOT double-count them.

## Comments

### 2026-06-13T20:10:00Z — root cause confirmed in prod DB; fix plan

### 2026-06-14T04:05:00Z — fixed (c7d712f), validated on real data
Detail endpoint now tz-aware (zoneinfo local-midnight bounds), contract gained the tz
param, frontend passes DEVICE_TZ. Prod-data check: the Jun-5 / Asia-Tbilisi window
[Jun-4 20:00, Jun-5 20:00) UTC returns exactly Face Pull / Shoulders / 2 sets — matches
the day card. core-api 508 tests (15 new tz/DST/422/back-compat), web 209, gate green.
