---
schema_version: 1
id: GYM-48
title: "Design: refine spec §11 History & set-editing via frontend-design plugin"
slug: gym-48-history-design-spec
status: backlog
priority: medium
type: research
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-46]
blocks: [GYM-49]
related: [GYM-12]
commits: []
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
- [ ] §11 appended with a concrete, buildable History/editor UX; nav-to-3-tabs defined; plugin invoked.

## Comments

### 2026-06-04T18:00:00Z — task created
Old MyTraining.tsx is a logic reference only — UI is reimagined from scratch.
