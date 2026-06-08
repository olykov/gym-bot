---
schema_version: 1
id: GYM-52
title: "apps/web: surface a 'couldn't save — restored' message on mutation error"
slug: gym-52-history-error-toast
status: done
priority: low
type: bug-fix
labels: [phase-5, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T21:35:00Z
start_date: 2026-06-08T22:50:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: [5767f41]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-52 — Surface mutation-error message in History

## Problem
GYM-49's set edit/delete are optimistic and roll back correctly on error, but the rollback is SILENT —
spec §11.4/§11.7 require a non-scary "couldn't save — restored" message so the user understands why
the value reverted. Without it a failed save looks like the app ignored the edit.

## Plan
Add a lightweight token-only toast/inline message (reuse `<ErrorState>` styling) fired from the
`onError` of the edit/delete mutations in `hooks/useTraining.ts` / `SetEditor.tsx`. Respect
reduced-motion. No new library.

## Acceptance criteria
- [ ] A failed edit/delete shows a brief "couldn't save — restored" message; build green.

## Comments

### 2026-06-04T21:35:00Z — task created
Flagged during the GYM-49 review. Minor (error-only path); does not block the History push.

### 2026-06-08T00:00:00Z — implemented (5767f41)

**Where the message fires:**
- Edit: `onError` callback wired in `SetEditor.save()` via `edit.mutate(…, { onError })` — calls `onEditError?.()` which the parent (`HistoryDay`) receives.
- Delete: `onError` callback wired in `SetEditor.confirmDelete()` via `del.mutate(…, { onError })` — calls `onDeleteError?.()`.
- Both are fired after TanStack Query's `onError` in `useTraining.ts` has already rolled back the optimistic patch (the cache is restored before the callback fires).

**Message text:**
- Edit: "Couldn't save — restored."
- Delete: "Couldn't delete — restored."

**Where the banner renders:**
- In `HistoryDay`, above the exercise card list, as a `<div aria-live="polite">` with a `<p>` inside.
- Auto-dismissed after 3 s via `setTimeout` in `showMutationError()`. The timer is reset on re-trigger and cleaned up on unmount.

**Styling reused:**
- Banner container: `rounded-md border border-hairline bg-secondary-bg px-3 py-2` — the same as the `createHint` banner in `SetLogger` (GYM-85).
- Text: `text-label text-accent` — matches the existing `create.isError` inline pattern in `SetLogger` §12.5.
- Tokens only; no new CSS or library.

**Reduced-motion:**
- The container has `transition-opacity duration-300 motion-reduce:transition-none`. No keyframe animations; Tailwind's `motion-reduce:` utility disables the opacity transition for users who have `prefers-reduced-motion: reduce`.

**Build result:** `tsc && vite build` — green, no errors or warnings.
