---
schema_version: 1
id: GYM-118
title: "Empty states still say 'log in the bot' — point them at the in-app record FAB"
slug: gym-118-empty-states-record-cta
status: review
priority: high
type: feature
labels: [frontend, ux, onboarding, copy]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:10:00Z
start_date: 2026-06-12T14:46:00Z
finish_date: null
updated: 2026-06-12T14:46:00Z
epic: ux-polish
depends_on: []
blocks: []
related: [GYM-109]
commits: []
tests: []
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-118 — Empty states → CTA to the record FAB

## Problem
Review doc 01 §1.3. Four empty states (Dashboard, Progress ×2, History) still say
"Log a set/workout **in the bot**…", while the Mini App record flow is now first-class.
The copy contradicts the product and hides the main CTA from new users.

## Solution
- Rewrite copy: "Tap **+** to log your first set" (per-surface variants).
- Use the existing (unused) `action` prop of `<EmptyState>`: an accent button that opens
  the RecordSheet. Plumbing: the sheet opener lives in `AppShell` state — expose it via a
  small context (or lift to a store) so pages can trigger it without prop-drilling.
- This doubles as FAB onboarding for first-run users.
- New strings land as i18n keys if GYM-109 is done by then; otherwise keep en literals and
  tag them for extraction.
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin.

## Acceptance criteria
- [x] No "in the bot" copy remains in `apps/web` (grep-verified; the only remaining match
      is the substring "in the bot[tom-nav]" inside a NavFab code comment, not UI copy).
- [x] Empty-state action opens the record sheet from Dashboard/Progress/History.
      (wiring code-verified; sheet-open behaviour needs an on-device tap check)
- [x] Empty path still fires zero extra queries (ARCH §2) — the context exposes a setter
      only; no new hooks/queries on the empty render path.

## Comments

### 2026-06-12T09:10:00Z — task created
P0 #2 from the review plan.

### 2026-06-12T14:46:00Z — implemented (agent wave 3b)
Files:
- `apps/web/src/components/record/RecordSheetContext.ts` (new) — minimal context:
  `RecordSheetContext` + `useRecordSheet()` exposing `openRecordSheet()`. Fail-fast throw
  outside the provider. No store library. Plain `.ts` (no JSX) so react-refresh lint
  stays clean.
- `apps/web/src/components/shell/AppShell.tsx` — open state stays here unchanged; a
  memoized `{ openRecordSheet }` provider now wraps the `<Outlet>` (inside Container).
  FAB keeps its existing `onRecord` prop path through BottomNav — not rewired.
- `apps/web/src/components/ui/EmptyState.tsx` — new `EmptyStateAction` (label+onClick):
  ≥44px accent-weak pill matching ErrorState's retry button (`press-95`, `text-accent`,
  `font-semibold`); `rounded-full` for the pill shape (the one deliberate deviation from
  ErrorState's `rounded-md`, per the "pill" requirement).
- `apps/web/src/pages/Dashboard.tsx`, `pages/History.tsx` — subline "Tap + to log your
  first set." + `EmptyStateAction "Log a set"` → `openRecordSheet()`.
- `apps/web/src/pages/Progress.tsx` — new-user state: same subline + button; the
  no-data-for-exercise state is COPY-ONLY ("No logged sets for {exercise}. Tap + to
  record one.") — the user already has data and the + FAB is one tap away, a second
  in-card button would be noise (per task guidance, deliberate choice).

Notes:
- i18n: GYM-109 is not done — strings stay as en literals on the existing
  `title`/`subtitle`/`label` props, all routed through `EmptyState`/`EmptyStateAction`,
  so extraction later is mechanical.
- Headlines (Bebas `title` prop) unchanged; sublines stay short Sora.

Verification: bench `npx tsc --noEmit` + `npm run lint` (max-warnings 0) + `npm run test`
(72 tests green) + `npm run build` — all pass. `grep -rn "in the bot" src/` → no UI copy.

Suggested commit: `Point empty states at in-app record CTA`
File overlap with GYM-117 (same wave): none — disjoint file sets.
