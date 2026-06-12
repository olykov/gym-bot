---
schema_version: 1
id: GYM-119
title: "Bug(verify): nested BottomSheets double-subscribe Telegram BackButton — one Back may close both"
slug: gym-119-nested-sheet-backbutton-stack
status: review
priority: high
type: bug-fix
labels: [frontend, bug, telegram, sheets]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:15:00Z
start_date: 2026-06-12T13:30:00Z
finish_date: null
updated: 2026-06-12T13:30:00Z
epic: ux-polish
depends_on: []
blocks: []
related: [GYM-82, GYM-98]
commits: []
tests: []
design_reports: ["docs/review/01-uiux-review.md", "docs/review/02-tech-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-119 — BackButton handler stack for nested sheets

## Problem
Review docs 01 §1.4 / 02 §5. `ManageSheet` (zIndex 40) opens over the record sheet; both are
`<BottomSheet>` and, while open, BOTH wire `WebApp.BackButton.onClick`. The SDK fires every
subscriber, so a single Back press likely runs both handlers (manage closes AND the record
sheet closes / picker steps back). Must be reproduced on a real device first.

## Solution
1. Reproduce: record sheet → long-press a tile → ManageSheet → press Telegram Back. Document
   the actual behavior (iOS + Android) in a comment.
2. Fix: a module-level back-handler STACK in `telegram/webapp.ts` — `pushBackHandler(fn)`
   returns a pop fn; exactly ONE SDK subscription dispatches to the top of the stack.
   `BottomSheet` switches from `wireBackButton` to push/pop on open/close. Top sheet
   consumes Back; the sheet below regains it on pop. BackButton visibility = stack non-empty
   (plus the HistoryDay route case).
3. Unit-test the stack module (pairs with GYM-124's vitest setup if available).

## Acceptance criteria
- [ ] One Back press closes ONLY the top-most sheet; second press acts on the next layer.
- [x] Record-picker step-back override still works (exercises → muscles → close).
- [x] HistoryDay route Back behavior unchanged.

## Comments

### 2026-06-12T09:15:00Z — task created
Flagged "verify then fix" — the double-subscribe is visible in code; the user-facing effect
needs device confirmation before/after.

### 2026-06-12T13:30:00Z — implemented (agent wave 2)

Files changed (this task's commit):
- `apps/web/src/telegram/webapp.ts` — module-level back-handler stack:
  `pushBackHandler(fn): () => void`. Exactly ONE SDK `BackButton.onClick` subscription,
  created lazily on first push, dispatching to the TOP of the stack only. Visibility is
  single-owner: show while the stack is non-empty, hide when it empties. The pop fn is
  idempotent (double-pop safe) and removes its own entry wherever it sits (out-of-order
  safe). Old `wireBackButton` / `showBackButton` / `hideBackButton` exports REMOVED —
  grep confirms zero remaining callers.
- `apps/web/src/components/ui/BottomSheet.tsx` — migrated to `pushBackHandler`; the
  `onBackOverride` semantics are preserved (override consumed → sheet stays open). The
  latest `onClose`/`onBackOverride` live in refs so the stack entry is pushed exactly once
  per open and a callback identity change can never pop+re-push it ABOVE a nested sheet.
  (This file also carries the GYM-125 focus trap — see overlap note below.)
- `apps/web/src/pages/HistoryDay.tsx` — migrated to `pushBackHandler` (route Back →
  `navigate(-1)`); still un-pushed while the set-editor sheet is open, so the sheet's
  handler is the only stack entry then, exactly as before.
- `apps/web/src/telegram/webapp.test.ts` (new) — 7 vitest tests with `@twa-dev/sdk`
  mocked via `vi.mock` + `vi.resetModules` per test: lazy single subscription, top-only
  dispatch, layer-below regains Back on pop, middle-entry pop, empty-stack dispatch
  no-op, show/hide visibility ownership, double-pop safety.

Behavior notes:
- With ManageSheet (zIndex 40) open over the record sheet, one Back press now runs ONLY
  ManageSheet's handler; the record sheet regains Back when ManageSheet pops.
- Criterion 1 left unticked: the stack logic is unit-tested, but the on-device
  reproduce/confirm (iOS + Android, record sheet → long-press tile → ManageSheet → Back)
  remains for the operator, per the task's "verify then fix" flag.
- Commit-split note: `BottomSheet.tsx` contains both this task's back-stack migration and
  GYM-125's focus trap. If strict per-task commits are wanted, commit GYM-125 first
  (its other files), then this task's commit carries `BottomSheet.tsx` with both edits —
  or accept the one-file overlap in whichever commit lands second.

Verification: bench run (`/tmp/bench/apps/web`) — `tsc --noEmit` clean, `eslint
--max-warnings 0` clean, `vitest run` 58/58 passed, `vite build` OK.

Suggested commit (GYM-119 files above):
`Add BackButton handler stack for nested sheets`
