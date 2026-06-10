---
schema_version: 1
id: GYM-114
title: "Search UX: drop match-reason badge; show a check + dimmed text for exercises already in the user's list"
slug: gym-114-search-owned-checkmark
status: done
priority: high
type: feature
labels: [frontend, design, ux, search, i18n]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T05:30:00Z
start_date: 2026-06-10T05:30:00Z
finish_date: 2026-06-10T00:00:00Z
updated: 2026-06-10T05:30:00Z
epic: tax-i18n
depends_on: []
blocks: []
related: [GYM-94, GYM-113]
commits: [896f4e4]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-114 — Search results: owned-checkmark instead of match-reason badge

## Problem
The add-exercise search dropdown (GYM-94, `ExerciseSearchField`) shows a right-side badge per candidate —
`aka` (alias) / `~` (fuzzy). The operator finds the badge noise. More useful: show which candidates the
user ALREADY HAS in the current muscle's list (so they see at a glance what's new vs already added).

## Solution (frontend-only if feasible)
- REMOVE the `match_reason` badge (`aka` / `~`) from every search result.
- For each candidate that is ALREADY in the user's exercise list for the selected muscle, show a
  **checkmark (✓)** on the right and render its name in a **dimmed / gray** color (uses a hint/muted token).
  New candidates (not yet in the list) render normally.
- "Create «…»" stays the last row. Picking an already-owned candidate behaves as today (selects it).
- Determine "already in the user's list" from data the picker already has (the muscle's exercise list that
  RecordPicker loaded). Match search candidates by exercise `id`. Consider HIDDEN exercises too (an exercise
  the user hid is still "theirs") — if the hidden set isn't readily available client-side, implement for the
  visible list and note the gap (do not add a backend/contract change without flagging it first).

## Acceptance
- [x] No `aka`/`~` badges in search results.
- [x] Candidates already in the muscle's list show a ✓ + dimmed name; new ones render normally.
- [x] Record flow unchanged; design tokens only; build + typecheck green; frontend-design plugin used.

## Comments

### 2026-06-10T05:30:00Z — start
Operator request (post search-quality fixes GYM-112/113). Delegated to frontend-design-engineer.

### 2026-06-10T00:00:00Z — done (SHA 896f4e4)
Branch: i18n/gym-114-owned-check

**What changed:**
- `ExerciseSearchField`: removed `MatchBadge` component and `showBadges` variable entirely.
  Added `ownedIds?: Set<number>` prop. Candidate rows: when candidate `id` is in `ownedIds`,
  name renders as `text-hint` (the `--hint` Telegram token = muted/dimmed) and a plain `✓`
  glyph (Unicode U+2713) appears on the right as a `text-hint` span at 13px. When not owned,
  name renders as `text-text` with no trailing mark. `aria-selected={isOwned}` on each row.
- `RecordPicker`: added `ownedExerciseIds` useMemo that unions `fullExercises.data` (visible
  exercises) + `hiddenExercises.data` (hidden exercises, already fetched by `useHiddenExercises`)
  into a `Set<number>` keyed by exercise id. Passed as `ownedIds` to both `ExerciseSearchField`
  call sites (main exercise step + empty-new-user path). No new queries — both data sources
  were already loaded before the search field opens.

**Hidden exercises:** INCLUDED. `hiddenExercises` is fetched by `useHiddenExercises(selectedMuscle)`
which is already live in RecordPicker. The ownedExerciseIds set unions both visible and hidden
exercise ids, so a hidden exercise will also get the ✓ + dim treatment in search.

**Token used for dim:** `text-hint` class → CSS variable `--hint` (Telegram themeParams, adapts
to light/dark automatically). No raw hex used anywhere.

**Check glyph:** Unicode `✓` (U+2713), rendered as plain text in a `shrink-0 text-[13px] text-hint` span.
The Tailwind `text-[13px]` is a one-off size class appropriate for a small indicator glyph.

**Green gate:** `tsc && vite build` passed clean — zero type errors, zero warnings, 2.79s build.
