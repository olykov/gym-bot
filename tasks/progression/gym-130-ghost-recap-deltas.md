---
schema_version: 1
id: GYM-130
title: "SetLogger ghost recap: Today vs Last time comparison + per-set deltas (ASC order)"
slug: gym-130-ghost-recap-deltas
status: review
priority: high
type: feature
labels: [frontend, record, progression, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T10:15:00Z
start_date: 2026-06-12T16:50:00Z
finish_date: null
updated: 2026-06-12T17:10:00Z
epic: progression
depends_on: []
blocks: [GYM-132]
related: [GYM-71, GYM-101, GYM-131]
commits: []
tests: []
design_reports: ["docs/review/03-progressive-overload-concept.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-130 — Ghost recap + deltas (Phase 1 core)

## Problem
Concept doc 03 §1 (approved). `log-context.last_session_sets` is only an invisible pre-fill;
there is no visible target while logging — no "fight yourself" moment. Operator pain:
no drive for progressive overload at the bench.

## Solution — ZERO API changes
- Recap becomes a two-column comparison: `TODAY | LAST TIME`, matched by set number from
  `log-context.last_session_sets`. Ghost rows (last-time only) in `--hint`, ~70% opacity.
- The next unbeaten ghost set is visible BEFORE Save — the standing target.
- Delta per saved set (operator decision #2: weight first, reps tiebreak):
  `▲ +2.5kg` (accent) / `▲ +1 rep` (accent, when weight equal) / `=` (hint) /
  `▼ −2.5kg` (hint — never punitive red).
- **Operator decision #1: recap returns to ASC** (Set 1 top) — rows must compare line-by-line.
  Reverts the GYM-101 DESC ordering; keep "last set visible" via auto-scroll of the recap
  region to the active row after save. Update the GYM-101 task file with a comment when done.
- Pure derivation functions (recap merge + delta calc) extracted and unit-tested (vitest,
  GYM-124).
- Tokens only; reduced-motion unaffected (this is layout, not motion).
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin (binding spec update:
  add the ghost-recap contract to frontend-spec §12.3 as part of this task).

## Acceptance criteria
- [x] Logging next to a prior session shows ghosts + per-set deltas exactly per doc 03 §1.
      (Row model + delta rule unit-tested; 360px visual pass → pending device check.)
- [x] No prior session → recap renders as today (no ghost column, no empty noise).
- [ ] Recap ASC + auto-scroll keeps the just-saved row visible on a 360px device.
      (ASC + scrollIntoView implemented and code-verified; real-device check pending.)
- [x] Unit tests for delta logic (weight-then-reps) green; spec §12.3 updated.

## Comments

### 2026-06-12T10:15:00Z — task created
Operator decisions 2026-06-12 locked: ASC; weight-priority deltas. The heart of Phase 1.

### 2026-06-12T17:10:00Z — implemented (agent wave 6a)

**Files.**
- `apps/web/src/components/record/derive.ts` — `mergeRecap` now ASC (GYM-130 reverts GYM-101 DESC);
  new pure exports: `Delta` (discriminated union up/down/eq), `FigurePair`, `ComparisonRow`,
  `computeDelta` (weight first, reps tiebreak — LOCKED), `buildComparisonRows` (union of today ∪
  last_session_sets, reuses mergeRecap for the today column → session > server > ✓-only preserved),
  `findNextGhostSet` (first unlogged ghost — the standing target).
- `apps/web/src/components/record/ComparisonRecap.tsx` — NEW presentational component: two-column
  TODAY | LAST TIME grid (shared 4-track template, one line per row at 360px, whitespace-nowrap),
  delta figure (accent ▲ / hint = / hint ▼, tabular), ghost rows with quiet `—` placeholder, plus the
  exact pre-GYM-130 single-column mode when no prior session exists.
- `apps/web/src/components/record/SetLogger.tsx` — uses `buildComparisonRows`; row-element registry
  (`Map<set, HTMLDivElement>`) + two auto-scroll effects: just-saved row after save
  (`scrollIntoView block:"nearest"`, smooth → instant under `prefers-reduced-motion`) and the next
  ghost target on Phase-B entry (instant, once per exercise). Header "Today" label kept only in
  single-column mode.
- `apps/web/src/components/ui/SetFigure.tsx` — optional `ghost` prop (`--hint`, ~70% opacity).
- `apps/web/src/i18n/messages.ts` — `recap.today`, `recap.lastTime`, `delta.upWeight`,
  `delta.downWeight` (MESSAGES) + `delta.upReps`, `delta.downReps` (PLURALS; ru invariant «повт.»),
  en+ru.
- `apps/web/src/components/record/derive.test.ts` — mergeRecap tests flipped to ASC; new suites:
  computeDelta matrix (weight up/down incl. reps-ignored cases, reps tiebreak both ways, eq),
  buildComparisonRows (union+ASC, ghost rows, ✓-only → no delta, session>server priority,
  no-prior-session passthrough, today-only extras), findNextGhostSet (3 cases). GYM-104 effectivePR
  suite untouched and green.
- `docs/frontend-spec.md` §12.3 — "Today recap" bullet block replaced with the comparison-recap
  contract (ASC, ghost column, LOCKED delta rule, auto-scroll, no-prior-session fallback), marked
  GYM-130; auto-advance bullet's "recap grows above" fixed to "grows below, auto-scrolled".
- `tasks/tax-fixes/gym-101-setlogger-recap-scroll.md` — append-only comment: ASC restored by GYM-130,
  visibility now via auto-scroll; GYM-101 layout regions unchanged.

**Decisions.**
- `Delta` typed `{kind:"up"|"down"|"eq"}` with metric/amount only on up/down (eq carries nothing).
- Down deltas include the kg unit (`▼ −2.5kg`, per doc 03 §1) and render `--hint` — never red.
- mergeRecap kept (not orphaned): it IS the today column inside buildComparisonRows, so the GYM-74
  priority invariant is enforced in one place.
- Ghost-row today placeholder is a single faint `—`, NOT `— · —` (which means "logged, numbers
  unknown" — GYM-123 #3 honesty preserved).
- Reps deltas via the PLURALS catalog (en rep/reps; ru invariant «повт.» across categories).
- ▲/▼ are unicode geometric figures (allowed), no emojis.

**Verification.** Bench (rsync → /tmp/bench): `tsc --noEmit` ✓, `npm run lint` (--max-warnings 0) ✓,
`vitest run` ✓ **127 tests** (was 112, +15), `npm run build` ✓. Pending: 360px visual + real-device
pass (Telegram iOS/Android — recap touch-scroll + scrollIntoView inside the sheet).

**Suggested commit:** `Add ghost recap comparison with per-set deltas`
