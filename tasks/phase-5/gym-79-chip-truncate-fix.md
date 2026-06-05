---
schema_version: 1
id: GYM-79
title: "apps/web: muscle Chip overflows its pill (no ellipsis) — fix flex truncation in Chip + all capped usages"
slug: gym-79-chip-truncate-fix
status: review
priority: high
type: bug-fix
labels: [phase-5, frontend, design, ux, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T14:10:00Z
start_date: 2026-06-05T14:10:00Z
finish_date: 2026-06-05T00:00:00Z
updated: 2026-06-05T00:00:00Z
epic: phase-5
depends_on: [GYM-77]
blocks: []
related: [GYM-74]
commits: [b6e322c]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-79 — Muscle Chip overflows its pill (no ellipsis)

## Problem (live, screenshot)
In History (and the same pattern in the record header + DayCard), a long muscle name in the chip/pill
does NOT ellipsize — the pink pill grows past its intended max-width and the text runs off-screen
(clipped by the viewport, not by a clean "…" inside the tag). Short names look fine.

## Root cause (diagnosed)
The flex-truncation footgun. At each call site the chip is wrapped in `<span maxWidth:8rem/10rem>` but:
1. The wrapper is a flex item with NO `min-width: 0`, so its default `min-width: auto` = min-content =
   the full nowrap text width → `max-width` is overridden, the item grows to the full name.
2. `Chip` is `inline-flex ... truncate`; `text-overflow: ellipsis` does not apply to an `inline-flex`
   box, so even when clipped there's no ellipsis.

## Plan (frontend-design-engineer — MANDATORY: invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only, no new lib)
- Fix `apps/web/src/components/ui/Chip.tsx` so a single-line label reliably ellipsizes within whatever
  width budget it's given: render the label as a block/inline-block that respects `max-width` and applies
  `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` to the TEXT (not an inline-flex box).
  Keep the pill look (rounded-full, `--accent-weak` fill, `--text`, Sora label, px-3/py-1) and the
  optional `title`. Allow an optional `className`/max-width passthrough so callers can set the cap on the
  chip itself.
- Fix the THREE capped call sites so the cap actually binds — add `min-w-0` to the flex wrapper (and keep
  the max-width), so the item can shrink and the chip ellipsizes:
  - `pages/HistoryDay.tsx:112` (muscle chip, 8rem)
  - `components/record/SetLogger.tsx:223` (record-header muscle pill, 8rem) — verify the header row gives
    the exercise name `min-w-0 flex-1` and the chip `min-w-0` so neither overflows.
  - `components/ui/DayCard.tsx:57` (muscle chips, 10rem; the `+N` overflow chip stays intact).
- Result: every muscle chip clips with a clean ellipsis inside the pill, never running past its
  max-width / off-screen, in both light & dark. Verify with a very long name (e.g. the operator's test
  muscles) at 360px width.

## Acceptance criteria
- [ ] Long muscle names ellipsize INSIDE the pill (no off-screen overflow) in History, record header, and
      DayCard; short names unchanged.
- [ ] `frontend-design` plugin invoked; tokens only; `npm run build` green.

## Comments

### 2026-06-05T14:10:00Z — task created
Live follow-up to GYM-77 (the max-width wrappers lacked min-w-0 and Chip used inline-flex, so ellipsis
never engaged). Caught in prod History view.

### 2026-06-05 — implementation (b6e322c)

**Chip.tsx**: Replaced `inline-flex … truncate` with an `inline-block` outer pill wrapping a
`block overflow-hidden text-ellipsis whitespace-nowrap` inner span. `text-overflow: ellipsis`
requires a block-level box; it silently does nothing on an `inline-flex` box, which is why
ellipsis never fired before. The outer pill keeps `inline-block max-w-full` so it still
sizes by content and respects any width cap the parent imposes. Added optional `className`
prop for callers to set extra constraints directly on the chip.

**Three call-site fixes** — added `min-w-0` to each flex-wrapper `<span>` so the flex item
can shrink below its content size and the `maxWidth` actually binds:
- `pages/HistoryDay.tsx` ~line 112: muscle chip, 8rem wrapper.
- `components/record/SetLogger.tsx` ~line 223: record-header muscle chip, 8rem wrapper;
  the exercise-name h2 already had `min-w-0 flex-1 truncate`.
- `components/ui/DayCard.tsx` ~line 57: muscle chips, 10rem wrapper; `+N` overflow chip
  untouched.

**Build result**: `tsc && vite build` — green, no TypeScript errors.

**Needs live-device pass**: verify on a real Telegram Mini App session at ~360px that a very
long muscle name (e.g. "Еще более длинное имя мышцы пусть будет добавлено вот так") shows a
clean ellipsis inside the pill in both light and dark themes.
