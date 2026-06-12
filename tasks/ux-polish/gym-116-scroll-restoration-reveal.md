---
schema_version: 1
id: GYM-116
title: "Bug: scroll position lost + reveal replays on back-navigation (Container re-key)"
slug: gym-116-scroll-restoration-reveal
status: review
priority: high
type: bug-fix
labels: [frontend, ux, navigation, motion]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:00:00Z
start_date: 2026-06-12T13:40:00Z
finish_date: null
updated: 2026-06-12T14:10:00Z
epic: ux-polish
depends_on: []
blocks: []
related: [GYM-121]
commits: []
tests: ["apps/web/src/components/shell/navigation.test.ts"]
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-116 — Scroll restoration + reveal only on forward nav

## Problem
Review doc 01 §1.1. `AppShell` renders `<Container revealKey={location.pathname}>`; `Container`
puts `key={revealKey}` on `<main>`, so EVERY navigation remounts the scroll container. Returning
from `/history/:date` to `/history` resets the list to the top AND replays the reveal stagger.
Painful on a 12+ week history list.

## Solution
- Stop re-keying `<main>` on route change.
- Reveal stagger plays on first mount / forward (push) navigation only — not on pop/back.
  (Pairs with GYM-121's directional transitions; do this one first, it is standalone.)
- Restore per-route scroll position (in-memory map keyed by `location.key`, or the
  react-router ScrollRestoration approach adapted to the custom scroll container).
- Consider replacing the `cloneElement` stagger hack with CSS `:nth-child` delays while here
  (see GYM-126 — coordinate, don't duplicate).
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin per CLAUDE.md.

## Acceptance criteria
- [ ] History → day → back lands at the previous scroll offset, no stagger replay.
      (implemented; needs device/browser smoke — visual behavior, not unit-testable)
- [ ] Forward navigation still gets the §9.4 reveal; reduced-motion unaffected.
      (implemented; reveal/reduced-motion are visual — verify on device)
- [x] No regression of the fixed-shell scroll model (only Container scrolls).

## Comments

### 2026-06-12T09:00:00Z — task created
P0 #1 from the UI/UX review prioritized plan.

### 2026-06-12T14:10:00Z — implemented (agent wave 3a)
Files changed:
- `apps/web/src/components/shell/Container.tsx` — `<main>` is never re-keyed anymore; the
  reveal moved to an inner wrapper (`reveal` boolean toggles `.reveal-stagger`, `replayKey`
  re-keys only the wrapper). `cloneElement` child-tagging removed. Forwards a ref to the
  scrolling `<main>` for scroll restoration.
- `apps/web/src/components/shell/useNavigationReveal.ts` (new) — reveal on first mount +
  PUSH/REPLACE only, never on POP; sticky `replayKey` advances only when the reveal plays.
- `apps/web/src/components/shell/scrollMemory.ts` (new) — pure per-`location.key` scroll
  store (unit-tested).
- `apps/web/src/components/shell/useScrollRestoration.ts` (new) — useLayoutEffect: restore
  saved offset on POP, scroll-to-top on PUSH/REPLACE; saves via a passive scroll listener so
  the value is read BEFORE the next route's shorter content clamps `scrollTop`.
- `apps/web/src/components/shell/AppShell.tsx` — wires both hooks + the main ref; no more
  `revealKey={location.pathname}`.
- `apps/web/src/index.css` — `.reveal`/`--reveal-i` replaced by CSS-only
  `.reveal-stagger > :nth-child` delays (cap: children 8+ share the max delay, they start
  below the fold); reduced-motion block updated accordingly.
- `apps/web/src/styles/tokens.css` — new `--reveal-step: 60ms` token (was a magic `60ms`).
- `apps/web/src/components/shell/navigation.test.ts` (new) — scroll-store unit tests.

Approach notes: router's `useNavigationType()` drives both reveal and restore. Initial load
reports POP, so first mount is special-cased (deep links still reveal). Stagger timing
unchanged vs spec §9.4: 8px rise, `--dur-reveal` 240ms, 60ms steps, instant under
prefers-reduced-motion. Known edge (accepted): restoring onto a cold-cache route clamps to
skeleton height — TanStack cache (staleTime 60s) makes this rare; re-restore-on-data is YAGNI.

Verification: `tsc --noEmit`, `eslint --max-warnings 0`, `vitest run` (67 tests, +9 new),
`vite build` — all green. Device smoke pending (review).

Overlap with GYM-121 (same session): `Container.tsx` also gains the `vt-content` class;
`index.css`/`tokens.css` carry both tasks' additions; `navigation.test.ts` covers both.

Suggested commit message: `Preserve scroll and skip reveal replay on back navigation`
