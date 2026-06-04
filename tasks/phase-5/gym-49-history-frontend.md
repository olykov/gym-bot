---
schema_version: 1
id: GYM-49
title: "apps/web: History tab — day list, day detail, set editor"
slug: gym-49-history-frontend
status: backlog
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-47, GYM-48]
blocks: [GYM-50]
related: [GYM-12]
commits: []
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
