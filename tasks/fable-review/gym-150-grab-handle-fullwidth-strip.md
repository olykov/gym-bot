---
schema_version: 1
id: GYM-150
title: "Sheet header strip: grab handle stretches full width because w-12 never generates"
slug: gym-150-grab-handle-fullwidth-strip
status: done
priority: critical
type: bug-fix
labels: [frontend, sheet, tailwind, miniapp, regression]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T20:38:00Z
start_date: 2026-06-12T20:38:00Z
finish_date: 2026-06-12T20:42:00Z
updated: 2026-06-12T20:42:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-147, GYM-149]
commits: [3fcad22]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-150 — The actual sheet "strip": grab handle rendered full width

## Problem (operator, on-device, persisted across GYM-147 and GYM-149)
A light horizontal strip across the sheet header would not go away. GYM-147 (border →
inset shadow) and GYM-149 (removed the inset, removed the top border) both targeted the
TOP EDGE — the wrong place. The operator was explicit: the strip is NOT the top rim; it
sits ~12px below the top, full width.

## Root cause (found by pixel pinpoint + built-CSS inspection)
The grab handle `<div className="mx-auto mb-4 h-1 w-12 rounded-full bg-hairline" />`
should be a 48px pill centred by `mx-auto`. But its rendered rect was `left:0, w:393`
— FULL WIDTH. Built CSS has `.h-1` but NO `.w-12`. Tailwind v4 sets `--spacing: initial`
in the theme and enumerates only `--spacing-0/1/2/3/4/6/8`; `w-12` needs `--spacing-12`,
which does not exist, so the utility is never generated. With no width, the block div
stretches to 100% and `bg-hairline` paints a full-width 4px bar = the strip. The GYM-148
page dimming made it stand out more.

## Fix
`w-12` → `w-[2.5rem]` (a literal/arbitrary value, always generated regardless of the
spacing scale). The handle is now a 40px pill centred at left:177 — `elementFromPoint`
at 12% and 85% width hits the empty (transparent) drag container, only the centre hits
the pill. No full-width strip.

## Verification (headless, dark, realistic insets, content behind)
- Grab pill rect: `left:177 w:40 h:4` (centred 40px), was `left:0 w:393`.
- Full-width luminance: the ~12px row is no longer a uniform bright band.
- Screenshot: clean centred grabber, no header strip.

## Comments

### 2026-06-12T20:42:00Z — fixed the real strip
GYM-147/149 fixed the top border/seam (real but different issues); this is the strip the
operator kept pointing at. Lesson: trust the pixel/DOM pinpoint over the top-edge
assumption — the culprit was a silently-ungenerated Tailwind width utility.
