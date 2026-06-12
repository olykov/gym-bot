---
schema_version: 1
id: GYM-133
title: "Progress: e1RM chart mode (Epley, client-side) + multi-type PR detection in SetLogger"
slug: gym-133-e1rm-chart-pr-types
status: review
priority: medium
type: feature
labels: [frontend, progress, progression, analytics]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:30:00Z
start_date: 2026-06-12T17:50:00Z
finish_date: null
updated: 2026-06-12T17:50:00Z
epic: progression
depends_on: []
blocks: []
related: [GYM-57, GYM-134, GYM-131]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-133 — e1RM mode + PR types (Phase 2, client-side part)

## Problem
Concept doc 03 §4.1. Weight-PR is the only progress signal; when weight plateaus but reps
grow, the user sees no progress. e1RM (Epley: `w × (1 + reps/30)`) captures both.

## Solution
1. **Progress chart**: third `SegmentedControl` mode "e1RM" — per-session max e1RM line,
   computed client-side from the existing exercise-progress series (mirror the "By Weight"
   client derivation; no API change). Tooltip: `e1RM 120kg (102.5 × 8)`.
2. **SetLogger PR types**: extend the PR-beat check beyond weight:
   - weight PR (exists) → full celebration (GYM-131 banner);
   - rep-PR at the same weight (more reps than ever at this weight — needs
     `log-context.last_session_sets` + pr only; if data insufficient, defer this subtype
     to GYM-134's endpoint and note it) → quiet chip flip + flare, NO banner;
   - e1RM PR (computed vs pr-derived e1RM) → quiet chip flip.
   Hierarchy: one celebration per save — the highest type wins.
3. Pure functions + unit tests (epley, PR-type resolution).

## Acceptance criteria
- [x] e1RM mode renders for any exercise with history; matches hand-computed values.
      (unit-tested against hand-computed Epley values; on-device check pending)
- [x] PR-type hierarchy fires exactly one celebration; weight-PR behavior unchanged.
      (resolver returns at most one kind; weight branch reproduces the GYM-104 check verbatim)

## Comments

### 2026-06-12T10:30:00Z — task created
Client-only by design; GYM-134 enriches it later with server-computed trends.

### 2026-06-12T17:50:00Z — implemented (agent wave 7a)
Files:
- `apps/web/src/lib/e1rm.ts` (new) — `epley(w, r)` (reps ≤ 0 → weight, defined edge),
  `roundE1rm` (1-decimal display rounding), `maxE1rmByDate` (per-date max-e1RM derivation
  for the chart, raw-value comparison, first-wins ties — mirrors By Weight).
- `apps/web/src/lib/e1rm.test.ts` (new) — 12 tests (formula, edges, derivation, ties,
  cross-series grouping, unparseable dates).
- `apps/web/src/components/progress/ExerciseProgressChart.tsx` — `ProgressMode` gains
  `"e1rm"`; new `byE1rmSeries` (one line, same theming/series ramp as By Weight); tooltip
  `e1RM: {v}kg ({w} × {r})` naming the source set; legend hidden in both single-line modes.
- `apps/web/src/pages/Progress.tsx` — third SegmentedControl option (i18n key).
- `apps/web/src/components/record/derive.ts` — `PrBeatKind` + `resolvePrBeat(serverPR,
  lastSessionSets, sessionSets, saved)`: hierarchy weight > reps-at-weight > e1rm, one
  kind per save; weight branch is the unchanged GYM-104 derived-effective-PR check.
- `apps/web/src/components/record/derive.test.ts` — 15 new resolver tests (hierarchy,
  ties, pool-max reps, e1RM tie, GYM-104 race, no-data cases).
- `apps/web/src/components/record/useSaveChoreography.ts` — `SaveEvent.beatPR: boolean`
  → `prBeat: PrBeatKind | null`; pulse + flare for ANY kind, banner for `"weight"` only.
- `apps/web/src/components/record/SetLogger.tsx` — calls `resolvePrBeat` at save time;
  `onSetLogged.beatPR` stays weight-PRs-only (GYM-132 summary count semantics unchanged).
- `apps/web/src/i18n/messages.ts` — `progress.e1rm`, `chart.e1rm` ("e1RM" Latin in en+ru).

Heuristic limitation (documented in `resolvePrBeat` docblock, accepted scope): the client
only holds log-context (`pr` + `last_session_sets`) plus this session's sets — not full
history. "Best-known reps at this weight" / "best-known e1RM" are LOWER BOUNDS over that
pool, so a quiet celebration may occasionally fire for a set an older unseen session
already beat. A real weight PR can never be missed (`pr` is the full-history max).
GYM-134's server-computed trend endpoint replaces the heuristic.

Verification (bench copy of apps/web): `npx tsc --noEmit` ✓, `npm run lint`
(--max-warnings 0) ✓, `npm run test` ✓ 163 tests (136 → 163, +27), `npm run build` ✓.
No new deps, no API changes. On-device check of the chart mode + quiet celebrations:
pending (next manual smoke).

Suggested commit message: `Add e1RM chart mode and multi-type PR detection`
