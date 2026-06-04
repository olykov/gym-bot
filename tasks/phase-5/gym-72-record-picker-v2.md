---
schema_version: 1
id: GYM-72
title: "apps/web: record picker v2 — continue-today + muscle/exercise tiles; last-session pre-fill; PR×reps; prefetch"
slug: gym-72-record-picker-v2
status: backlog
priority: high
type: feature
labels: [phase-5, frontend, design, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T08:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T08:00:00Z
epic: phase-5
depends_on: [GYM-70, GYM-71]
blocks: []
related: [GYM-64, GYM-69]
commits: []
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
