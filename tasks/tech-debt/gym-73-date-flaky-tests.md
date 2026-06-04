---
schema_version: 1
id: GYM-73
title: "Tests: fix 5 date-hardcoded analytics/history tests that break on day rollover"
slug: gym-73-date-flaky-tests
status: review
priority: high
type: bug-fix
labels: [tech-debt, api, tests]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T10:00:00Z
start_date: 2026-06-05T10:10:00Z
finish_date: 2026-06-05T00:45:00Z
updated: 2026-06-05T10:10:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-39, GYM-47, GYM-56]
commits: [bc4e931763ac273a454155763b0213aebee48433]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-73 — Date-flaky tests

## Problem
5 tests assume a fixed "today" / date window and fail after a calendar-day rollover (passed on
2026-06-04, fail on 2026-06-05). They are NOT a product regression — the endpoints are correct — but a
red suite hides real regressions.
- `tests/test_analytics_endpoints.py::TestActivityEndpoint::test_activity_contains_today`
- `tests/test_analytics_endpoints.py::TestActivityEndpoint::test_activity_cross_user_isolation`
- `tests/test_training_history.py::TestListTrainingDays::test_today_appears_with_correct_counts`
- `tests/test_training_history.py::TestListTrainingDays::test_cross_user_isolation`
- `tests/test_training_history.py::TestGetTrainingDay::test_cross_user_isolation`

## Plan
Make the dates dynamic: seed relative to `datetime.utcnow()` and assert against the same computed
"today"/window (or freeze time with a fixture) instead of a hardcoded `2026-06-04`. The conftest seeds
at `NOW()`, so the test windows/expected-counts must derive from the current date, not a literal.

## Acceptance criteria
- [ ] Full `apps/api` suite green on any calendar day (no hardcoded today/date window).

## Comments

### 2026-06-05T10:00:00Z — task created
Surfaced during GYM-71 (its own 18 tests pass; these 5 are pre-existing date-flakiness).

### 2026-06-05T00:45:00Z — fixed (bc4e931)
Root cause: the machine runs in UTC+4, so `date.today()` returned `2026-06-05` (local) while
`NOW()` in the DB seed (and the endpoints' UTC day boundaries) produced `2026-06-04` (UTC).
The 5 failing tests built their query window and assertions around `date.today()`, so they
queried a day that had no seed data.

Fix: replaced `date.today()` with `datetime.utcnow().date()` in all 5 affected test bodies
in `test_analytics_endpoints.py` and `test_training_history.py`. No product code was changed.

Result: `pytest tests/ -q` — 154 passed, 0 failed (confirmed on two consecutive runs).
