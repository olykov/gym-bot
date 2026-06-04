---
schema_version: 1
id: GYM-48
title: "Design: refine spec §11 History & set-editing via frontend-design plugin"
slug: gym-48-history-design-spec
status: done
priority: medium
type: research
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-04T19:15:00Z
finish_date: 2026-06-04T20:35:00Z
updated: 2026-06-04T12:00:21Z
epic: phase-5
depends_on: [GYM-46]
blocks: [GYM-49]
related: [GYM-12]
commits: [ae03771]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-48 — Design: History & set-editing UX (spec §11)

## Problem
The old admin training view was a flat, non-scrolling id-only table — unusable on mobile. The new
History tab must be fully rethought via the frontend-design plugin: day-browser + day-detail +
set-editor, convenient and consistent with "Chalk & Iron".

## Plan (design-agent — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
Append `docs/frontend-spec.md` §11 "History & set-editing" (do not weaken §0–§10): concrete UX for
the **day list** (card per day: date, muscle chips, exercises/sets counts), the **day detail**
(exercises → sets, Telegram BackButton), and the **set editor** (bottom-sheet, weight/reps steppers,
Telegram MainButton + haptic to save, swipe/affordance to delete, optimistic update + invalidate
analytics queries). Define the bottom-nav move to 3 tabs (Dashboard · Progress · History), the
number-input ergonomics (≥44px, no jitter, tabular-nums), empty/loading/error, reduced-motion. Reuse
GYM-41 primitives; add only what's missing (e.g. BottomSheet, Stepper). Orchestrator reviews after.

## Acceptance criteria
- [x] §11 appended with a concrete, buildable History/editor UX; nav-to-3-tabs defined; plugin invoked.

## Comments

### 2026-06-04T18:00:00Z — task created
Old MyTraining.tsx is a logic reference only — UI is reimagined from scratch.

### 2026-06-04T12:00:21Z — §11 refined; review (commit ae03771)
Invoked the `frontend-design` plugin first (HARD RULE #1), then appended `docs/frontend-spec.md`
**§11 "History & set-editing (v1)"** and updated §10.1's BottomNav note to 3 tabs. Applied the
already-committed **"Chalk & Iron"** aesthetic (§9) — did not re-pick. Key decisions, all bound to
the real contract shapes:
- **Nav → 3 tabs** Dashboard · Progress · History (`/history`, `/history/:date`); History glyph =
  stacked-bars log mark; Distribution · Profile stay reserved.
- **Day list:** `<DayCard>` per day from `GET /training/days` — Bebas date heading (`MON 02 JUN`),
  `--accent-weak` muscle chips, Sora `{exercises} · {sets}` counts, chevron, whole card taps to detail.
  **Window-based pagination** (the contract has only `from`/`to`, no offset): default last ~12 weeks,
  expand-backward on an IntersectionObserver sentinel; query key `["training","days",from,to]`.
- **Day detail:** Telegram `BackButton`; exercises grouped as `<Card>`s, sets as `<SetRow>`
  (`Set 1 — 100kg × 8`, tabular-nums); tap row → editor, swipe-left → delete. Key
  `["training","day",date]`.
- **Set editor:** `<BottomSheet>` with two `<Stepper>`s (Weight min0/step2.5/`inputmode=decimal`,
  Reps integer/step1, ≥44px, Bebas tabular-nums), Telegram **MainButton** save + success haptic →
  `PUT /training/{training_id}`; **two-step in-sheet delete confirm** (warning haptic) →
  `DELETE /training/{training_id}`. Optimistic `onMutate` + rollback; invalidates
  day/days/summary/activity/exercise-progress so Dashboard + Progress refresh.
- **New primitives:** `<BottomSheet>`, `<Stepper>`/`<NumberField>`, `<DayCard>`, `<SetRow>`
  (reuse Card/Divider/Skeleton/EmptyState/ErrorState/ListRow).
- Full skeleton/empty/error states, light+dark, all motion behind `prefers-reduced-motion`; §11.7
  gaps/risks (fat-finger delete, optimistic rollback, decimal weight, large day, whale pagination,
  cross-screen staleness, `training_id`-as-key, BackButton ownership). Validator: 51 files OK.
  Unblocks GYM-49.
