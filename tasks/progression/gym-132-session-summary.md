---
schema_version: 1
id: GYM-132
title: "Session summary on Done — one glance, one tap to dismiss, zero added friction"
slug: gym-132-session-summary
status: review
priority: high
type: feature
labels: [frontend, record, progression, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:25:00Z
start_date: 2026-06-12T17:15:00Z
finish_date: null
updated: 2026-06-12T17:40:00Z
epic: progression
depends_on: [GYM-130]
blocks: []
related: [GYM-131]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-132 — Session summary on Done

## Problem
Concept doc 03 §3. "Done" closes the sheet silently — the session ends with no closing
moment. Operator decision #3: build it, BUT it must not lengthen the fast logging
experience in any way.

## Solution — speed constraints are the spec
- On Done with ≥1 set logged this session: body-swap (same sheet, like Phase A↔B) to a
  summary panel; with 0 sets → close immediately, no summary ever.
- Content (all computed CLIENT-side from sessionSets + log-context + cached summary —
  zero network wait): `12 sets · 3 exercises · 5,840 kg volume`,
  `▲ N sets beat last session · M PR` (needs GYM-130 delta logic), `Week streak: 7`.
- **Dismiss = one tap ANYWHERE** (whole panel + scrim + Back + auto-dismiss after ~4s —
  pick auto-dismiss length at impl, or drop auto-dismiss if it feels rushed). No buttons
  required, no scroll, fits 360px without scrolling.
- Restrained tone — an account, not a celebration (no exclamation marks).
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin; spec §12 addition.

## Acceptance criteria
- [x] Done → summary → tap → closed: total added time ≤1s of user attention; 0-set path
      unchanged (instant close).
      (Implemented: whole panel = one dismiss button + ~4s auto-dismiss + scrim/Back as
      usual; empty session log → `onClose()` directly, no summary render. The ≤1s
      attention feel → pending device check.)
- [x] All numbers correct from cache only (verified offline-ish: no spinner ever).
      (Everything from the in-memory session log; week streak via `qc.getQueryData` —
      never a fetch, the line is omitted on cache miss. No loading state exists in the
      component at all. Math unit-tested.)
- [x] Cross-screen invalidation on final close unchanged (§12.5 contract).
      (Verified: invalidation fires per save in `useCreateTraining.onSettled`, not on
      close; every summary dismiss path calls the SAME RecordSheet `onClose` as before.)

## Comments

### 2026-06-12T10:25:00Z — task created
Operator decision #3 with the explicit "не удлинять опыт записи" constraint encoded in the
acceptance criteria.

### 2026-06-12T17:40:00Z — implemented (agent wave 6b)

**Files.**
- `apps/web/src/components/record/derive.ts` — pure additions: `SessionLogEntry`
  ({muscle, exercise, set, weight, reps, beatLast, beatPR}), `SessionSummary`,
  `summarizeSession(log)` (sets, distinct {muscle,exercise} pairs via a NUL-separator
  key, Σ weight×reps volume, beatLast count, PR count), `beatsLastSession(ghosts, saved)`
  (the GYM-130 LOCKED delta rule vs the same-set-number ghost; no ghost → false).
- `apps/web/src/components/record/derive.test.ts` — new suites: `beatsLastSession`
  (no-match, weight up, reps tiebreak, eq/down) and `summarizeSession` (empty log = all
  zeros, totals + volume math, same-named exercise under another muscle is distinct,
  beat/PR counts independent, half-kilo volume exact). +9 tests.
- `apps/web/src/components/record/SessionSummaryPanel.tsx` — NEW: the whole panel is a
  single `<button>` (one tap anywhere dismisses); ~4 short lines + "Tap to close" hint,
  fits 360px with no scrolling; stats line in tabular Bebas; "▲ N sets beat last
  session · M PR" parts rendered only when non-zero (never "▲ 0 sets…"); week-streak
  line from the cached `/analytics/summary` only (`qc.getQueryData` via the queryKeys
  factory — omitted when not cached, no fetch); auto-dismiss timer
  `SUMMARY_AUTO_DISMISS_MS = 4000`, cleared on unmount, runs under reduced motion too
  (a timer is not motion). Volume via `Intl.NumberFormat(locale)` (en "5,840" /
  ru "5 840"), one fraction digit for half-kilo plates. No exclamation marks.
- `apps/web/src/components/record/RecordSheet.tsx` — owns the session: `sessionLogRef`
  (a ref — appends never re-render the sheet mid-logging) accumulating every saved set
  across ALL exercises via `handleSetLogged`; `handleDone` (wired ONLY to SetLogger's
  Done button) body-swaps to `<SessionSummaryPanel>` when the log is non-empty, else
  closes immediately; scrim/Back/drag-dismiss keep calling `onClose` directly as today;
  close-reset effect also clears the log + summary flag.
- `apps/web/src/components/record/SetLogger.tsx` — new required `onSetLogged` prop:
  reports each successful save with `beatLast` (computed at save time from
  `log-context.last_session_sets` via `beatsLastSession`) and `beatPR` (the existing
  GYM-104 `beat`). Per-exercise `sessionSets` behavior unchanged.
- `apps/web/src/i18n/messages.ts` — `sessionSummary.title/volume/prCount/weekStreak/
  tapToClose` (MESSAGES) + `sessionSummary.beatLast` (PLURALS, en one/other + ru
  one/few/many), en+ru, restrained tone.

**Decisions.**
- Session log lifted to RecordSheet as a **ref**, not state — zero extra renders on the
  hot logging path (the speed constraint is the spec); the summary reads it on Done.
- Done is the ONLY entry into the summary (operator constraint): scrim, Telegram Back,
  Esc and drag-dismiss are untouched close paths. While the summary is up, all of those
  still close (same BottomSheet wiring).
- Zero-progress sessions show no "▲ 0…" line — an account, not a lie and not noise.
- Auto-dismiss kept at 4s (operator left length to impl); the timer is independent of
  reduced-motion (it is not motion). Double-fire (tap + timer) is safe — `onClose` is
  idempotent.
- `beatLast` snapshot is taken at save time (against the ghost the user actually saw),
  not recomputed later — honest to the moment of the lift.

**Verification.** Bench (rsync → /tmp/bench): `tsc --noEmit` ✓, `npm run lint`
(--max-warnings 0) ✓, `vitest run` ✓ **136 tests** (was 127, +9), `npm run build` ✓.
Pending: device pass — Done→tap rhythm ≤1s attention, 360px fit, dark mode, offline-ish
check (airplane mode: summary must render instantly with no spinner).

**Overlap note.** Shares `SetLogger.tsx` and `messages.ts` with GYM-131 (same wave).
Suggested order: commit GYM-131 first, then GYM-132 with `SetLogger.tsx` +
`messages.ts` included here (SetLogger's `onSetLogged` needs RecordSheet to compile);
or one combined commit referencing both tasks.

**Suggested commit:** `Add session summary on Done with one-tap dismiss`
