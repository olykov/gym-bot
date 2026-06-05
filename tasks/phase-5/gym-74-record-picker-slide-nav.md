---
schema_version: 1
id: GYM-74
title: "apps/web: picker slide-nav (muscle→exercise push) + fixed-height sheet + today recap w×r fix"
slug: gym-74-record-picker-slide-nav
status: in_progress
priority: high
type: feature
labels: [phase-5, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T11:00:00Z
start_date: 2026-06-05T11:00:00Z
finish_date: null
updated: 2026-06-05T11:00:00Z
epic: phase-5
depends_on: [GYM-72]
blocks: []
related: [GYM-64, GYM-69]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-74 — Picker slide-nav + fixed-height sheet + today-recap w×r fix

## Problem (operator feedback on live v2)
1. **Today recap loses values on reopen/Continue.** Sets logged this session show `Set 1 — 100kg × 8`,
   but after closing+reopening or entering via Continue they collapse to `Set 1 ✓` (checkmark only) —
   because the recap then reads `completed_sets` (set NUMBERS only) instead of the actual weight/reps.
2. **Muscle→exercise should be a horizontal screen transition, not the sheet growing.** Today picking a
   muscle expands the sheet (exercises appear below → height jumps). Operator wants a navigation PUSH:
   tap a muscle → muscles slide LEFT out, that muscle's exercises slide IN from the right, with a Back
   affordance. Plus: the sheet a bit TALLER and FIXED height (no jump between steps), muscle tiles a
   bit BIGGER, layout that handles variable-length muscle names + custom muscles, and the sheet must
   NEVER overlap the app header. Animation fast, intuitive, non-flickering — user always knows where a
   view came from and how to go back.

## Plan (frontend-design-engineer — MANDATORY: invoke `/frontend-design:frontend-design` and ultrathink the layout; keep the app's consistent Chalk & Iron design; tokens only, no new lib)

### #1 — today recap shows real w×r after reopen/Continue
- The recap of today's sets for the chosen exercise must show `Set n — {weight}kg × {reps}`, not
  `Set n ✓`, regardless of whether the sheet was just opened, reopened, or entered via Continue.
- Source today's sets-with-values from `GET /training/day/{today}` (already fetched/prefetched for the
  Continue tile; its `TrainingDayExercise.sets` carry `{set, weight, reps}`) filtered to the chosen
  exercise. Merge with this-session sets (session takes precedence for a just-saved set). NO API change.
- Auto set# still = `max(today's set numbers ∪ session) + 1`. Pre-fill logic (GYM-72 last_session_sets)
  unchanged.

### #2 — slide-nav picker + fixed taller sheet (ultrathink the layout via the plugin)
- **Two in-sheet steps as a horizontal PUSH** (muscle list → exercise list), e.g. a translateX track:
  picking a muscle slides muscles out left and the exercises in from the right; a Back control (and the
  Telegram BackButton, §11.7) slides back. Fast (~180–240ms), eased, reduced-motion → instant swap,
  no flicker. The Continue tile + faint divider stay on the muscle (root) step.
- **Fixed sheet height across both steps** so nothing jumps — pick a height that fits the typical tile
  grid AND **never overlaps the app header** (respect the AppShell fixed header + safe-area top inset;
  the sheet's max height must stay below the header). The frontend designer decides the exact
  height/inset math via the plugin.
- **Bigger muscle tiles** in a **responsive grid** that tolerates variable-length labels + custom
  muscles (operator unsure on columns — designer decides: e.g. an auto-fit grid, not a hardcoded 3-up,
  so long names + custom entries don't break). Exercise tiles in the same tile language. Keep top-N +
  "Show all" (§12.9) and add-inline `+ Muscle` / `+ Exercise`.
- Keep everything else from GYM-72 intact (Continue tile, faint divider, last-session pre-fill, PR chip
  `{w}kg × {r}`, one log-context call + prefetch + long cache, auto-advance, PR-beat, light+dark,
  reduced-motion, sticky in-sheet Save).
- Update `docs/frontend-spec.md` §12.2/§12.3 (picker = slide-nav + fixed height) and note the recap
  source change.

## Acceptance criteria
- [ ] Today recap shows `Set n — {w}kg × {r}` after reopen/Continue (not `Set n ✓`).
- [ ] Muscle→exercise is a horizontal push with Back; sheet height fixed (no jump) and never overlaps
      the header; muscle tiles bigger + responsive to label length / custom muscles; animation fast,
      intuitive, non-flickering; reduced-motion safe.
- [ ] `frontend-design` plugin invoked; Chalk & Iron consistency; `npm run build` green; spec updated.

## Comments

### 2026-06-05T11:00:00Z — task created
Operator-reviewed iteration on GYM-72. Frontend-design plugin mandatory; orchestrator reviews the build.
