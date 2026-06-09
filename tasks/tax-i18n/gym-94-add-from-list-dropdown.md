---
schema_version: 1
id: GYM-94
title: "Frontend: add-exercise = search-and-pick dropdown (suggestions first; free-text create-as-is last resort)"
slug: gym-94-add-from-list-dropdown
status: done
priority: medium
type: feature
labels: [taxonomy, frontend, design, ux, i18n]
assignee: null
model: claude-sonnet-4-6
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-10T00:00:00Z
finish_date: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
epic: tax-i18n
depends_on: [GYM-93, GYM-108]
blocks: []
related: []
commits: [53b729f]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-94 — Add-from-list dropdown

## Problem
Today add-exercise is free text → fragmentation. Make it a search-and-pick over the canonical catalog so
users mostly choose prepared names. Per ADR 0001.

## Scope (layers): frontend (design plugin)
- As the user types, show ranked canonical suggestions (GYM-93) in the muscle. Picking one creates/links to
  the canonical (with the user's language name). 
- Free-text "create '<typed>' as a new exercise" is offered ONLY as the last resort, after suggestions, when
  nothing fits. This trains users onto canonical names.
- Keep Chalk & Iron; reuse the picker/manage-sheet language; mobile-first.

## Key decisions (operator)
- Suggestions first; free-text create only if nothing in the list fits.

## Acceptance
- [x] Add-exercise shows canonical suggestions as you type; pick = canonical/link; free-text create is the
      last-resort fallback; design consistent; build green.

## Comments

### 2026-06-10 — Implementation (53b729f)

**What changed:**
- `apps/web/src/api/analytics.ts` — added `ExerciseCandidate` type export + `searchExercises(q, muscleId?, lang?, limit?, signal?)` function calling `GET /exercises/search`.
- `apps/web/src/hooks/useRecord.ts` — added `useExerciseSearch(q, muscleId, lang, limit)` hook: debounced via `debouncedQ`, disabled when q is empty or muscleId is null (respects ARCH §2 empty-path rule), `staleTime: 30s`, `placeholderData` keeps the previous candidate list visible while a new query is in-flight.
- `apps/web/src/components/record/ExerciseSearchField.tsx` — new component: debounced 250ms input (search icon, autoCapitalize words, autoFocus), ranked candidate list (`max-h-[256px] overflow-y-auto`), match-reason badge (only `alias` → "aka", `fuzzy` → "~"; exact/prefix are silent), a dashed "Create «…»" row always last (last-resort). Tokens-only, Chalk & Iron design.
- `apps/web/src/components/record/RecordPicker.tsx` — exercise step: `+ Exercise` button opens `ExerciseSearchField` instead of `AddInlineField`. Picking a candidate calls `onPick` directly (no mutation, same path as tapping a tile). Creating calls `submitExercise` (existing `POST /exercises` path, unchanged). Empty-new-user path: uses `ExerciseSearchField` when `selectedMuscleId` is resolved; falls back to `AddInlineField` when the muscle id is not yet in cache (race-safe).

**Green gate:** `tsc && vite build` — zero TypeScript errors, clean build (2.97s).

**No regression:** muscle selection, tile picking, logging a set, recap, continue tile, hidden items expander — all untouched. `submitExercise` / `onPick` downstream paths unchanged.
