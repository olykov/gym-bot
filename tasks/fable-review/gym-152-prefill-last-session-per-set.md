---
schema_version: 1
id: GYM-152
title: "Set prefill: next set should mirror last training's same set, not repeat this session's last set"
slug: gym-152-prefill-last-session-per-set
status: done
priority: high
type: feature
labels: [frontend, record, ux, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T06:45:00Z
updated: 2026-06-13T06:45:00Z
start_date: 2026-06-13T00:00:00Z
finish_date: 2026-06-13T00:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [aa60662]
tests:
  - apps/web/src/components/record/derive.test.ts
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-152 — Prefill the next set from last training's same set

## Problem (operator)
Recording: set 1 prefilled 50×10 → enter → saved → set 2's fields stay 50×10 (a repeat of
this session's set 1) instead of what set 2 was LAST training. We want fast recording with a
meaningful per-set target.

## Current behaviour (`SetLogger.tsx` prefill priority, §12.3)
1. repeat this session's previous set; 2. `last_session_sets` matched by set number (ONLY
when the session has no sets yet); 3. empty. So after set 1, set 2 repeats set 1.

## Decision (operator-approved)
Flip the priority to mirror last training per set:
1. **`last_session_sets` matched by the current set number** (last training's set N).
2. Fallback: repeat this session's last set (more sets than last time / new exercise).
3. Empty (Save disabled until valid).

Data already cached by the log-context (`ctx.data.last_session_sets`, feeds the recap) — no
extra request. Only fill EMPTY fields (never fight a mid-edit user). Predictable: set N always
shows last training's set N; matches the "vs LAST TIME" recap framing.

Trade-off accepted: same-session weight bumps won't carry to the next set (user re-bumps);
acceptable since progression is intentional and last weight is visible in the recap.

## Plan (client-frontend-engineer — pure logic, no plugin)
Reorder the prefill effect in `SetLogger.tsx`: prefer `last_session_sets.find(set === nextSet)`
over `sessionSets[last]`, with the session-repeat as fallback. Keep the "only fill empty"
guard and the re-run-after-save behaviour. Add/adjust unit tests for the new priority.

## Comments

### 2026-06-13T06:45:00Z — filed + approved for this iteration

### 2026-06-13T10:49:00Z — implemented and closed
Added `derivePrefill(nextSet, sessionSets, lastSessionSets)` pure helper to `derive.ts`
(primary: last_session_sets[N], fallback: session repeat, else empty). Updated `SetLogger.tsx`
prefill effect to call it. Added 8 unit tests in `derive.test.ts` covering cases (a)–(d).
All 205 tests pass; 0 lint warnings. Build pre-existing errors unchanged (not introduced here).
