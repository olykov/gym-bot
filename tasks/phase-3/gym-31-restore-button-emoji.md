---
schema_version: 1
id: GYM-31
title: "Hotfix: GYM-28 rewrite stripped button emoji to ASCII"
slug: gym-31-restore-button-emoji
status: in_progress
priority: high
type: bug-fix
labels: [phase-3, bot, ui]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T14:42:26Z
start_date: 2026-06-01T14:42:26Z
finish_date: null
updated: 2026-06-01T14:42:26Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-28, GYM-10]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-31 — Hotfix: GYM-28 rewrite stripped button emoji to ASCII

## Problem
After the Phase 3 deploy the operator reported: buttons lost their emoji on all buttons,
and "color" disappeared on some. Root cause: the GYM-28 bot-engineer rewrite of
`apps/bot/utils/markups.py` (async API migration) replaced every unicode emoji in button
text with ASCII placeholders — `➕`→`+` (Add Muscle/Exercise), `⬅️`→`<-` (Go back/Cancel),
`❌`→`X` (Delete Exercise, per-exercise delete). The colorful emoji glyphs (red ❌, blue ⬅️,
green ➕) are what the operator perceived as "color" on those buttons.

Diff against the pre-GYM-28 version (bfacfb1) confirmed the `ButtonStyle` background colors
(SUCCESS/PRIMARY/DANGER + the PR weight / max-reps green highlight) were NOT changed — only
the emoji text was stripped.

## Solution
Restore the original unicode emoji in all 12 affected button labels; leave every `ButtonStyle`
and the `_is_peak()` PR-highlight logic untouched. Verified: 0 ASCII placeholders remain, 8
`ButtonStyle.` usages preserved (matches original), file compiles.

## Comments

### 2026-06-01T14:42:26Z — start
Surgical text-only restore in markups.py. No handler/data-flow change needed: both weight/reps
markup call sites already pass (user_id, muscle, exercise[, weight]); PR color is data-dependent
and the code path matches the original. Deploy + Telegram smoke to close.
