---
schema_version: 1
id: GYM-50
title: "Bot: point the Mini App button at the History tab (deep-link)"
slug: gym-50-bot-deeplink-history
status: backlog
priority: low
type: feature
labels: [phase-5, bot]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-49]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-50 — Bot: Mini App button → History

## Problem
After the Phase 5 cutover the bot's "Edit trainings" WebApp button opens the analytics app root, not
an editor. Now that History (view + edit) exists, the button should open it directly and be renamed
to match.

## Plan
In `apps/bot/utils/markups.py`, deep-link the WebApp button to the History tab — append a route
hint to `WEB_APP_URL` (e.g. `…/#/history`) or pass `tgWebAppStartParam` that apps/web maps to the
History route (coordinate the param name with GYM-49). Rename the button to fit (e.g. "My trainings"
/ "History"). Follow the telegram-design skill (color = signal; keep callback_data/FSM unaffected).
Verify the WebApp opens straight on History.

## Acceptance criteria
- [ ] The bot button opens apps/web directly on the History tab; label matches the destination.

## Comments

### 2026-06-04T18:00:00Z — task created
Confirm Telegram forwards start_param into the WebApp; otherwise use the URL fragment.
