---
schema_version: 1
id: GYM-49
title: "apps/web: History tab — day list, day detail, set editor"
slug: gym-49-history-frontend
status: review
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-04T20:40:00Z
finish_date: 2026-06-04T21:30:00Z
updated: 2026-06-04T21:30:00Z
epic: phase-5
depends_on: [GYM-47, GYM-48]
blocks: [GYM-50]
related: [GYM-12]
commits: [0cdccf6276ac97bcb61ad263e218dda1d8ce5c3c]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-49 — apps/web: History tab

## Problem
Build the view + edit feature on the existing shell, per the refined spec §11.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md §11)
- Add the **History** tab to the bottom-nav (Dashboard · Progress · History).
- **Day list:** `GET /training/days` → cards (date, muscle chips, exercises/sets counts), paginated,
  reverse-chrono. Tap → day detail (route + Telegram BackButton).
- **Day detail:** `GET /training/day/{date}` → exercises with their sets (set #, weight × reps).
- **Set editor:** bottom-sheet with weight/reps steppers → `PUT /training/{id}`; delete → 
  `DELETE /training/{id}`. Telegram MainButton + haptic to save; optimistic update + invalidate the
  affected TanStack Query keys (day, days, summary, activity) so Dashboard/Progress refresh.
- States first-class (skeleton/empty/error); tokens only; mobile-first; light+dark; reduced-motion.
- Old `apps/admin/src/pages/MyTraining.tsx` + `TrainingModal.tsx` = logic reference only.

## Acceptance criteria
- [ ] Browse days → open a day → edit a set's weight/reps (persists) → delete a set (persists);
      Dashboard/Progress reflect the change. Build green; spec §7 + §11 satisfied; plugin invoked.

## Comments

### 2026-06-04T18:00:00Z — task created
This is the feature that makes the bot's Mini App button meaningful again (GYM-50 deep-links to it).

### 2026-06-04T21:30:00Z — implemented (review)
`frontend-design` skill invoked at the start of the design pass (mandatory). Built per spec §11 on the
existing GYM-41/42 shell + primitives — no shell/chrome/primitive re-invention, no new deps.

Components built (all token-only, `apps/web/` only):
- Nav → 3 tabs: added **History** to `components/shell/navConfig.tsx` (stacked-bars "log" glyph); routes
  `/history` + `/history/:date` under `<AppShell>`. Shell title resolver shows the day in Bebas on the
  detail route (§11.3) while the History tab stays active.
- `pages/History.tsx` — `<DayCard>` list from `GET /training/days`, **window-based pagination** (default
  ~12 weeks, IntersectionObserver sentinel expands `from` backward a step, "Load earlier" Card fallback,
  stops when the earliest day stops moving). Query key `["training","days",from,to]`. Skeleton×5 /
  no-trainings EmptyState / window-exhausted footer / ErrorState.
- `pages/HistoryDay.tsx` — Telegram BackButton → list; `GET /training/day/{date}`; exercises grouped as
  `<Card>`s with a `<SetRow>` per set; tap row → editor sheet, swipe-left → reveals Delete (routes through
  the in-sheet confirm). Empty-day / 404 EmptyState; auto `navigate(-1)` when the last set is deleted.
  Query key `["training","day",date]`.
- New primitives in `components/ui/`: `<BottomSheet>` (grab-handle, scrim, safe-area, §9.5 hairline,
  240ms slide behind reduced-motion, BackButton-closes-sheet-first per §11.7), `<Stepper>`/`<NumberField>`
  (±44px buttons + typed input, comma→dot normalize, weight step 2.5 decimal / reps integer),
  `<DayCard>`, `<SetRow>`, `<Chip>` (no chip primitive existed; ChipRow is a Progress selector).
- `components/history/SetEditor.tsx` — sheet contents: two steppers, Telegram **MainButton SAVE**
  (showProgress + `notificationOccurred('success')`, disabled when unchanged/invalid), secondary
  **two-step in-sheet Delete confirm** (`notificationOccurred('warning')`).
- `hooks/useTraining.ts` mirroring `useAnalytics.ts`; `api/training.ts` fetchers typed by `@api-contract`.

Optimistic + invalidation wiring (§11.4): both mutations snapshot in `onMutate`, patch/remove the set by
`training_id` (never list index, §11.7), roll back in `onError`, and on `onSettled` invalidate
`["training","day",date]`, `["training","days"]`, `["analytics","summary"]`, `["analytics","activity"]`,
`["analytics","exercise-progress"]`. Day-emptiness after delete read from the live query cache (not the
stale hook closure).

Build: `npm run build` (tsc + vite) **green** — 715 modules, no TS errors (noUnusedLocals/Parameters on).
The >500kB chunk warning is the pre-existing ECharts bundle, unchanged by this task.

Needs a live Telegram/browser pass: the real edit/delete round-trip + rollback message, MainButton SAVE
feel, sheet slide + focus, swipe-to-reveal feel on a touch device, and dark-mode contrast of the muscle
chips, the SetRow hairline, and the sheet scrim over near-black `--bg`. Edit-error currently rolls back
the row (cache restore) but does not yet surface a "couldn't save — restored" toast — a v1 follow-up.
