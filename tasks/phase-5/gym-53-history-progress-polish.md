---
schema_version: 1
id: GYM-53
title: "apps/web polish: delete UX (MainButton overlap), chart axis, header border, scroll flash"
slug: gym-53-history-progress-polish
status: in_progress
priority: high
type: bug-fix
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T22:00:00Z
start_date: 2026-06-04T22:00:00Z
finish_date: null
updated: 2026-06-04T22:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12, GYM-42]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-53 — apps/web polish (operator-reported)

## Problem
Four visual/UX bugs found on the live Mini App (operator smoke):
1. **Delete doesn't work / isn't visible** — the in-sheet "Delete set" button sits at the BOTTOM of
   the `<BottomSheet>`, but the Telegram native **MainButton (SAVE)** renders over the bottom of the
   WebApp viewport → it covers the Delete button. Must rethink within Mini App constraints (keep the
   frontend-design plugin approach): move delete OUT of the bottom strip the MainButton owns.
2. **Progress chart axis overlap** — the bold month/year x-axis label overlaps the day numbers.
3. **Header border under the blur** — `AppHeader` has BOTH `border-b border-hairline` AND the scrim
   blur; the hard hairline peeks under the soft scrim (looks accidental).
4. **White flash on infinite scroll** — expanding the day-list window changes the query key
   (`["training","days",from,to]`) → new query, no cached data → ~1s blank before the list returns.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
1. Make delete reliably visible+working while MainButton owns the screen bottom: place the delete
   affordance in the sheet HEADER (e.g. a clear "Delete" / trash control by the exercise title), keep
   the two-step confirm + warning haptic. Ensure no interactive sheet content hides under MainButton.
2. Fix the ECharts x-axis label collision (formatter/interval/rotate) so month/year and day don't
   overlap; keep §10.5 token theming.
3. Drop the header `border-b`; let the scrim be the only separator (keep the blur the operator likes).
4. `placeholderData: keepPreviousData` (TanStack v5) on the day-list query so the list stays while a
   wider window loads — no blank flash.

## Acceptance criteria
- [ ] Delete works + is visible (not under MainButton); chart axis legible; header has no stray
      border under the scrim; no white flash on load-more. Build green; plugin invoked.

## Comments

### 2026-06-04T22:00:00Z — operator-reported, in progress
Roots diagnosed by the orchestrator: MainButton overlap (#1), ECharts axis (#2), header border+scrim
(#3), query-key change without keepPreviousData (#4).
