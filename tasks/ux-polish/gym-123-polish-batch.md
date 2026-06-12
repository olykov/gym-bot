---
schema_version: 1
id: GYM-123
title: "UX polish batch: P2 items from the 2026-06 review (doc 01 §4–§5)"
slug: gym-123-polish-batch
status: review
priority: medium
type: chore
labels: [frontend, ux, polish, a11y]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:35:00Z
start_date: 2026-06-12T15:10:00Z
finish_date: null
updated: 2026-06-12T15:10:00Z
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

# GYM-123 — Polish batch (P2)

## Problem
Review doc 01 §4–§5: a pile of small, independent polish items — each ≤ a few hours, none
deserving its own task. Batched; tick them off in this file as they land (one commit may
close several).

## Checklist
- [x] `StatCard` has `press-95` but isn't tappable — remove the press state OR make cards
      entry points (Sets → History, Streak → streak-rule explainer). Decide at impl.
      *Decision: removed the press state; entry-point navigation deferred as feature creep.*
- [x] Activity grid: month labels row above the columns (orientation in 26 weeks).
      *Pure `monthLabels()` helper (month transitions, ≥3-column overlap guard) + unit tests;
      tiny Sora --hint row, same size idiom as the weekday rail.*
- [x] SetLogger recap `Set n ✓` rows: align style with `w×r` rows (`— · —` in the same
      tabular figure style) instead of a bare checkmark.
      *Muted text-hint, same tabular/display classes — no fabricated numbers.*
- [x] `ErrorState` "❌" emoji → token-stroked inline SVG (brand consistency).
      *20px circle+X stroked `var(--accent)` (graphical accent use, §9.3-OK), aria-hidden.*
- [x] AuthGate pending: drop "Loading / Signing you in…" EmptyState — skeleton shell only.
      *Frame + skeleton cards/grid kept; added `role="status"` for AT.*
- [x] `aria-live="polite"` region on the SetLogger recap (new set announced).
- [x] Done button: light success haptic on session close (until GYM-132 supersedes).
      *`hapticImpact("light")` (impact, not notification — success notification is for saves).*
- [x] Dark-theme contrast QA pass: collect the 4 "verify in dark" spec items + `--hint`
      on `--secondary-bg` label cases into one checked list; fix what fails 4.5:1 (text)
      / 3:1 (large/graphical).
      *Dark palette passes everywhere (hint 4.78–5.47:1, accent 5.48–6.28:1) — no dark
      token bump needed. Light --hint is 2.92–3.25:1 (below 4.5:1 small text) but --hint
      is Telegram-owned at runtime, so token churn has no in-Telegram reach — documented
      in the comment below instead of changing tokens.*
- [x] ECharts tooltip on touch: ensure tap (not only hold) shows point values
      (`triggerOn` fallback on coarse pointers).
      *Explicit `triggerOn: "mousemove|click"` in the shared `baseChartOption` tooltip.*

## Acceptance criteria
- [ ] All checklist items closed (or explicitly dropped with a comment).

## Comments

### 2026-06-12T09:35:00Z — task created
UI work → `frontend-design-engineer` agent + `frontend-design` plugin per CLAUDE.md.

### 2026-06-12T15:10:00Z — implemented (agent wave 4b)

**Files changed**
- `apps/web/src/components/ui/StatCard.tsx` — #1: removed `press-95` from the Card (not
  tappable; entry-point navigation deliberately NOT built — feature creep for this wave).
- `apps/web/src/components/dashboard/activityGridModel.ts` — #2: new pure `monthLabels()`
  helper: label on each column whose month (first/Monday cell) differs from the previous
  column's; first column never labelled; labels < 3 columns after the previous one are
  skipped so nowrap labels can't overlap at 26 columns.
- `apps/web/src/components/dashboard/activityGridModel.test.ts` — #2: 5 new unit tests
  (full-window expected labels, first-column rule, min-gap skip, padding, empty).
- `apps/web/src/components/dashboard/ActivityGrid.tsx` — #2: month-labels row above the
  columns (Sora --hint, 0.625rem — same idiom as the weekday rail; flex-1 slots with the
  same gap-1 so they align 1:1 with grid columns; `aria-hidden`, dates already live on
  cells). Weekday rail got a matching h-3 spacer so rows stay level. Ring-only/static —
  no new motion, nothing to gate for reduced motion.
- `apps/web/src/components/record/SetLogger.tsx` — #3: pre-session `Set n` rows now show
  `— · —` in the same `tabular font-display text-title` figure style, muted `text-hint`
  (honest placeholder, no fabricated numbers); #6: recap `<section>` is
  `aria-live="polite"` so a newly appended set row is announced; #7: Done fires
  `hapticImpact("light")` before `onDone` (impact, not the success notification — that
  one is reserved for saves; GYM-132's session summary will supersede this).
- `apps/web/src/components/ui/ErrorState.tsx` — #4: the "❌" emoji replaced with a 20px
  inline SVG (circle + X), stroke `var(--accent)`, `aria-hidden`, stacked above the
  message. Accent chosen over --hint: it reads as an error mark and is graphical accent
  use (a11y-OK per spec §9.3); message text stays `--text`.
- `apps/web/src/auth/AuthGate.tsx` — #5: pending state no longer renders the
  "Loading / Signing you in…" EmptyState; skeleton shell only (frame + 2 skeleton cards +
  skeleton grid), with `role="status" aria-label="Loading"` so AT isn't left silent.
- `apps/web/src/components/charts/echartsTheme.ts` — #9: shared tooltip now sets
  `triggerOn: "mousemove|click"` explicitly so a plain tap shows values on coarse
  pointers, independent of ECharts' version default.

**#8 dark-contrast QA findings (WCAG ratios from tokens.css fallback hexes; real
Telegram themes vary — these are the out-of-Telegram / first-paint values):**
- DARK: `--hint` #8a8f99 on `--bg` #17181a = 5.47:1, on `--secondary-bg` #232427 =
  4.78:1 (both pass 4.5:1); `--accent` #ff6a4d on `--bg` = 6.28:1, on `--secondary-bg` =
  5.48:1 (pass even as small text); `--text` on `--bg` = 15.72:1. Empty grid cell
  (white@4% over --bg) keeps its 1px `--grid-empty-border` — visible. **No dark token
  changes needed.**
- LIGHT: `--hint` on `--bg` = 3.25:1, on `--secondary-bg` = 2.92:1 — below 4.5:1 for
  small text (label text on Stepper value box, SetLogger createHint box, ManageSheet
  muted rows, skeleton-adjacent labels). `--accent` #e5482f on `--bg` = 3.96:1 — ≥3:1 so
  large/graphical use is fine (§9.3 rule holds), but the small accent error lines
  (`text-label text-accent` in SetLogger/ManageSheet/etc.) sit below 4.5:1.
- Decision (conservative, per task): **document, don't churn tokens** — `--hint` is
  Telegram-owned at runtime (`theme.ts` overwrites it from themeParams on load +
  themeChanged), so bumping the light fallback only affects out-of-Telegram dev
  rendering while drifting from Telegram's native hint convention. Revisit small accent
  error text (maybe `--text` + accent icon) in GYM-127 (tokens consolidation).

**Verification:** bench (`/tmp/bench/apps/web`): `npx tsc --noEmit` PASS, `npm run lint`
PASS (0 warnings), `npm run test` PASS (86 tests, incl. 5 new `monthLabels` tests),
`npm run build` PASS. No new dependencies.

**Suggested commit message:** `Polish batch: grid month labels, recap style, a11y`
