---
schema_version: 1
id: GYM-58
title: "Analytics in the user's timezone (streak, activity grid, day boundaries)"
slug: gym-58-user-timezone-analytics
status: review
priority: low
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T00:00:00Z
start_date: 2026-06-08T23:10:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: phase-5
depends_on: [GYM-56]
blocks: []
related: [GYM-12, GYM-39]
commits: [54d4144, a5db3f3]
tests: [apps/api/tests/test_gym58_timezone.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-58 — User-timezone analytics

## Problem
All day/week boundaries in analytics (streak, activity grid, day grouping in History) are computed in
**UTC**. `training.date` is a naive `TIMESTAMP` written as UTC `NOW()`. Near midnight a session can land
on the "wrong" calendar day/week for a non-UTC user (the operator is Georgia +4), skewing the streak,
the activity grid, and which History day a set appears under.

## Plan (deferred)
Make day/week boundaries timezone-aware: either store `training.date` as `TIMESTAMPTZ` (a db migration),
or accept a per-request timezone / per-user timezone (a `users.timezone` column the bot sets from
Telegram) and apply it in the `DATE_TRUNC`/grouping of all analytics + history queries. Update streak
(GYM-56), activity grid (GYM-39), and day grouping (GYM-47) consistently. Cache key must include tz.

## Acceptance criteria
- [ ] Day/week boundaries follow the user's timezone across streak, activity grid, and History.

## Comments

### 2026-06-05T00:00:00Z — task created
Deferred from the iteration; operator chose UTC for now. Touches db (TIMESTAMPTZ or users.timezone) +
all analytics grouping — sizable, so backlog.

### 2026-06-08 — API implementation (a5db3f3)
Added optional `tz` query parameter (IANA timezone name) to `GET /analytics/activity`,
`GET /analytics/summary`, and `GET /training/days` in `apps/api`.

**AT TIME ZONE transform**: when `tz` is provided, the raw naive UTC timestamp column
is converted with `date AT TIME ZONE 'UTC' AT TIME ZONE :tz` in SELECT/GROUP BY/ORDER BY.
This appears only in those clauses — never in the WHERE predicate — so the index on
`(user_id, date)` is still used for the date-range scan (sargable). `tz` is passed as a
bound parameter (`:tz`), never string-interpolated.

**Streak anchor handling**: the `get_analytics_summary` endpoint uses
`datetime.now(tz_info).date()` as the `today_ref` anchor when `tz` is given (instead of
the UTC-based `datetime.now(timezone.utc).date()`). The weekly bucketing SQL also uses
the `AT TIME ZONE` transform so both the anchor and the bucket boundaries agree on the
user's local week.

**tz validation**: `zoneinfo.ZoneInfo(tz)` (stdlib) is called before any DB access;
an unknown/invalid name raises `ZoneInfoNotFoundError` which is caught and re-raised as
HTTP 422 with a clear message. `None` (default) skips validation and preserves the exact
UTC behaviour.

**Cache-key change**: `tz or "UTC"` is included in the `make_key(...)` call for both
`activity` and `summary` so a UTC-result and a tz-result for the same user never collide.

**Full test suite result**: 370 passed, 0 failed (`cd apps/api && python3 -m pytest tests/ -q`).

### 2026-06-08 — contract slice (54d4144)
Contract-only slice landed. Added a reusable `TimezoneQuery` parameter component (`tz`: optional
string, IANA timezone name e.g. "Asia/Tbilisi") and referenced it from the three day/week-grouping
operations: `GET /analytics/activity` (daily grid), `GET /analytics/summary` (weekly streak),
`GET /training/days` (day grouping). Optional and fully backward-compatible: when omitted, boundaries
stay UTC (unchanged). Not added to non-grouping endpoints.

`make validate` passes (OpenAPI 3.1, 36 paths). Both clients regenerated: TypeScript (`schema.ts`,
gitignored) type-checks clean under `tsc --strict` and shows `tz?` on all three operations; Python
`models.py` regenerated and compiles (only the regen timestamp changed — query params don't produce
response-schema models; the `tz` arg is plumbed in the hand-maintained `client.py` wrapper when the
API/clients consume it). status stays in_progress: the API impl + DB grouping (core-api-engineer /
db-migration-steward) and client wiring remain.
