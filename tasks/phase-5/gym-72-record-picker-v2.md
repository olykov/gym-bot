---
schema_version: 1
id: GYM-72
title: "apps/web: record picker v2 — continue-today + muscle/exercise tiles; last-session pre-fill; PR×reps; prefetch"
slug: gym-72-record-picker-v2
status: done
priority: high
type: feature
labels: [phase-5, frontend, design, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T08:00:00Z
start_date: 2026-06-05T10:05:00Z
finish_date: 2026-06-05T10:45:00Z
updated: 2026-06-05T10:45:00Z
epic: phase-5
depends_on: [GYM-70, GYM-71]
blocks: []
related: [GYM-64, GYM-69]
commits: [2f4baef]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-72 — Record picker v2 + pre-fill + perf (operator feedback)

## Problem
Operator feedback on the live record flow: (1) the 8-item Recent block is useless (just-logged
exercises aren't what you want next); (3) selected-exercise data loads noticeably slowly; (4) pre-fill
should be the last recorded value of that set #, not the PR; (5) the PR chip should read "{w}kg × {r}";
(6) restructure the picker.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin/skill; keep the app's consistent design)
- **Picker v2 (§12.2 restructure):** remove the 8-item recent fast lane. Top = a single **"Continue"**
  card/tile — the **last exercise trained TODAY** (from `GET /training/day/{today}`); tap → Phase B. A
  **light, subtle divider** below it (the agent decides the right hairline/treatment via the plugin —
  operator wants it very light/unobtrusive). Below the divider: **muscle tiles** (frequency-sorted,
  `top-muscles`) → on pick, **exercise tiles** in the SAME pretty tile format (top ~6 + "Show all",
  §12.9). If not trained today, no Continue card (just muscle/exercise tiles).
- **Phase B pre-fill (#4):** use the new `GET /analytics/log-context` (GYM-71). Pre-fill set N priority:
  (1) this session's previous set for the exercise; (2) `last_session_sets` set N; (3) empty. **Drop the
  PR pre-fill.** Auto set# from `completed_sets ∪ session`.
- **PR chip (#5):** render `PR {weight}kg × {reps}` (from `log-context.pr`).
- **Perf (#3):** one `log-context` call replaces the 3 Phase-B reads. **Prefetch**: on sheet open warm
  `top-muscles` + `day/today`; on muscle pick prefetch its exercises; optionally prefetch `log-context`
  for the Continue exercise. Long `staleTime`/`gcTime` so the session stays instant after first warm.
- Keep auto-advance, PR-beat, invalidation (§12.5, add `log-context`), states, light+dark, reduced-motion.
  Update `docs/frontend-spec.md` §12.2/§12.3 to match. Reuse all §11/§12 primitives; no new lib.

## Acceptance criteria
- [ ] Picker = Continue-today + light divider + muscle/exercise tiles (recent-8 gone); pre-fill = last
      recorded set-N (not PR); PR chip "{w}kg × {r}"; one log-context call + prefetch (snappy); build
      green; plugin invoked; consistent with the app's design.

## Comments

### 2026-06-05T08:00:00Z — task created
Operator-reviewed iteration on GYM-69. Frontend-design plugin mandatory; orchestrator reviews the build.

### 2026-06-05T10:45:00Z — implemented (commit 2f4baef), → review
`frontend-design` plugin invoked before the UI pass (mandatory). Kept the committed Chalk & Iron
look — distinctive in the details, disciplined in the structure (one card/tile style, tokens only,
no new lib).

**Picker restructure (§12.2 v2).** Removed the 8-item "Recent" fast lane and `useRecentExercises`/
`recent-exercises` from the flow. New top-to-bottom layout:
- **Continue tile** — the last exercise trained TODAY, derived client-side from
  `GET /training/day/{today}` as the exercise group whose set has the highest `training_id` (the
  day-detail API orders alphabetically, not chronologically, so array position can't be trusted —
  `training_id` is a serial id, highest = latest insert). Full-width tile reusing the tile language
  (rounded-lg, hairline, `--secondary-bg`, press-95) with a "CONTINUE TODAY" eyebrow + chevron
  (DayCard grammar). Omitted entirely when nothing was trained today.
- **Muscle tiles → exercise tiles** in the SAME tile format (the old Recent-chip style, ≥52px), top
  ~6 + client-side "Show all" expand (§12.9). Kept add-inline `+ Muscle` / `+ Exercise`.

**Divider treatment.** Operator wanted "совсем лёгкий, ненавязчивый". Chose a new
`.record-divider-faint` utility: an inset hairline (width ~2/3, centered) masked to **transparent at
both ends** via a horizontal `--hairline` gradient — the §9.5 "dissolve" idea at micro scale, softer
than the canonical hard `<Divider>`. Token-only (no magic colour), rendered ONLY when the Continue
tile is present.

**Pre-fill change (#4).** Drop the PR pre-fill. Phase B now reads ONE
`GET /analytics/log-context?muscle&exercise&date=today`. Pre-fill priority for set N: (1) this
session's previous set (sheet state); (2) `last_session_sets` matched on the same set number (the
actual last working set for that set); (3) empty + `--hint`, Save disabled until valid. Auto set# =
`max(completed_sets ∪ session) + 1`. Recomputed after each save so the next set's last-session value
fills.

**PR chip (#5).** Renders `PR {weight}kg × {reps}` from `log-context.pr`; a session PR with no reps
source drops the `× {reps}`.

**Perf / prefetch (#3).** One `log-context` call replaces the old 3 Phase-B reads (1 round-trip).
Prefetch helpers in `useRecord.ts`: on sheet open warm `top-muscles` + `day/{today}` + the Continue
exercise's `log-context`; on muscle pick prefetch its exercises. Long `staleTime`/`gcTime` (10m) on
all record reads so a warmed session stays instant. `useCreateTraining` invalidation updated: added
`["analytics","log-context",…]`, dropped the old completed-sets/personal-record/recent keys (§12.5).

Kept auto-advance, PR-beat, states, light+dark, reduced-motion, sticky in-sheet Save. Spec §12.2/
§12.3 (+ §12.4/§12.5/§12.6 references) updated; §12.1 nav + §12.9 decisions left intact.

**Build:** `cd apps/web && npm run build` (tsc + vite) is GREEN — 724 modules, built in ~2.9s (only
the pre-existing ECharts chunk-size warning).

**Needs a live device pass:** Continue-tile correctness when several exercises share the same minute;
the faint divider's visibility in Telegram dark over near-black `--bg`; last-session pre-fill against
real data; prefetch warmth (perceived snappiness) on a real connection.
