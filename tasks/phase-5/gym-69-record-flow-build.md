---
schema_version: 1
id: GYM-69
title: "apps/web: record-training flow (sheet — pick + log set, pre-fill, auto-advance)"
slug: gym-69-record-flow-build
status: backlog
priority: high
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: [GYM-66, GYM-67, GYM-68]
blocks: []
related: [GYM-64]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-69 — Record-training flow

## Problem
Build the record flow the center FAB opens, per spec §12.2–12.9 — super smooth, ~1 tap per extra set.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md §12)
- `<RecordSheet>` (controller over the existing `<BottomSheet>`) wired to the GYM-68 FAB; two phases
  (body-swap), BackButton-closes-sheet-first.
- **Phase A `<RecordPicker>`:** fast lane = `GET /analytics/recent-exercises` chips (1 tap); browse by
  muscle (`top-muscles` → `top-exercises?limit=200`, render top ~6 + **"Show all"** client-side expand,
  §12.9); add-inline `+ Muscle` / `+ Exercise` (`POST /muscles`/`POST /exercises`). Empty new-user path
  → add-first-exercise prompt.
- **Phase B `<SetLogger>`:** today recap (`completed-sets` ∪ session), auto set #, two `<Stepper>`s
  pre-filled — same-session last set, else the `recent-exercises` last working set, else PR, else empty;
  PR chip; in-sheet sticky SAVE (§11.4) → `POST /training`; success haptic; **auto-advance re-arms in
  place** (+1 tap/set); PR-beat accent pulse; "← Switch exercise" / "Done".
- Cross-screen invalidation on save-settle / close: summary, activity, completed-sets, personal-record,
  exercise-progress, training days + today (§12.5). Write-error keeps the sheet open, no false recap.
- States/empty/error/light+dark/reduced-motion (§12.6); tokens only; reuse §11 primitives.

## Acceptance criteria
- [ ] FAB opens the sheet; log a set end-to-end (pick → pre-filled → SAVE) and additional sets at ~1 tap;
      Dashboard/Progress/History reflect it; tap-budget (§12.3) met; build green; plugin invoked.

## Comments

### 2026-06-05T06:00:00Z — task created
The heart of GYM-64. Depends on the recent-exercises endpoint (GYM-67) + the FAB (GYM-68).
