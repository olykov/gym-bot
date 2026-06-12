---
schema_version: 1
id: GYM-121
title: "Directional route transitions: push slide-left / pop slide-right (View Transitions)"
slug: gym-121-route-transitions
status: review
priority: medium
type: feature
labels: [frontend, ux, motion, navigation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:25:00Z
start_date: 2026-06-12T13:40:00Z
finish_date: null
updated: 2026-06-12T14:15:00Z
epic: ux-polish
depends_on: [GYM-116]
blocks: []
related: []
commits: []
tests: ["apps/web/src/components/shell/navigation.test.ts"]
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-121 — Directional route transitions

## Problem
Review doc 01 §3. `/history` → `/history/:date` drill-in has no direction — content just
re-staggers in place. Mobile-native pattern: push slides left, pop slides right. The slide
language already exists inside RecordPicker; extend it to routes.

## Solution
- Use the View Transitions API (`document.startViewTransition`) keyed on nav direction
  (POP vs PUSH from react-router's navigation type). Unsupported browsers / reduced-motion
  degrade to instant — exactly the reduced-motion contract.
- Tab switches (bottom-nav): keep the current instant swap + indicator slide — directional
  slides between 4 tabs get noisy; transition applies to drill-in routes only
  (`/history/:date`, future detail routes).
- Depends on GYM-116 (scroll restoration must not fight the transition snapshot).
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin.

## Acceptance criteria
- [ ] History → day slides left; Back slides right; ~240ms `--ease-out-soft`.
      (implemented via `--dur-reveal`/`--ease-out-soft`; slide direction/feel needs device
      smoke — Telegram WebView View-Transitions support varies per client)
- [x] Reduced-motion / unsupported WebView → instant, no errors.
      (feature gate `resolveViewTransition` unit-tested; fallback path is the exact pre-task
      `navigate()` call, plus a try/catch around a throwing API)
- [x] Tab switches unaffected. (tabs never call `useTransitionNavigate`; without the
      `data-nav-transition` attribute no transition CSS matches and no API call is made)

## Comments

### 2026-06-12T09:25:00Z — task created

### 2026-06-12T14:15:00Z — implemented (agent wave 3a)
Files changed:
- `apps/web/src/components/shell/useTransitionNavigate.ts` (new) — the single integration
  point: wraps `useNavigate`, accepts `(to, "forward" | "back")`. Feature-detects
  `document.startViewTransition` + prefers-reduced-motion via pure `resolveViewTransition()`
  (exported, unit-tested); when supported, sets `data-nav-transition="push|pop"` on `<html>`,
  runs the navigation inside the transition with `flushSync` (so GYM-116's layout-effect
  scroll restore commits inside the snapshot callback), and clears the attribute on
  `finished` (with catch + a sync try/catch fallback for throwing WebViews). No router
  upgrade, no library, no new deps.
- `apps/web/src/index.css` — `.vt-content { view-transition-name: drill-content }` +
  directional `::view-transition-old/new(drill-content)` keyframes keyed on the root
  attribute (push: out-left/in-right; pop: out-right/in-left), `--dur-reveal` 240ms,
  `--ease-out-soft`, slide distance `--slide-drill`. Reduced-motion block also neutralises
  any snapshot animation (belt-and-braces). Header/bottom-nav stay in the default root
  snapshot (near-identical cross-fade) so the §2 fixed shell holds still.
- `apps/web/src/styles/tokens.css` — new `--slide-drill: 24px` token (24 is on the spacing
  scale; a subtle slide+fade matching the §9.4 8px-rise language, not a full-width sweep).
- `apps/web/src/components/shell/Container.tsx` — `vt-content` class on the scrolling
  `<main>` (only the content area animates).
- `apps/web/src/components/ui/DayCard.tsx` — `transitionNavigate(.., "forward")` (push).
- `apps/web/src/pages/HistoryDay.tsx` — Telegram-Back handler and empty-day exit both use
  `transitionNavigate(-1, "back")` (pop). Future detail routes opt in the same way.
- `apps/web/src/components/shell/navigation.test.ts` (new) — feature-gate unit tests.

Approach notes: direction comes from the caller (drill-in semantics), not from history
introspection — KISS, and it keeps tab switches instant by construction. Device-tune later
if desired: slide distance, and whether the PUSH reveal stagger + slide together feel busy
(they compose today; suppressing reveal during a transition was deliberately not built —
YAGNI until seen on device).

Verification: `tsc --noEmit`, `eslint --max-warnings 0`, `vitest run` (67 tests), `vite
build` — all green. Visual/device smoke pending (review).

Overlap with GYM-116 (same session): both tasks touch `Container.tsx`, `index.css`,
`tokens.css`, `HistoryDay.tsx` (116 removed `useNavigate` there) and share
`navigation.test.ts` — if committed separately, split hunks accordingly or commit 116 first.

Suggested commit message: `Add directional view transitions for history drill-in`
