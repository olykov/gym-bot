---
schema_version: 1
id: GYM-144
title: "Mini App serves stale bundle after deploy — index.html cached by Telegram webview"
slug: gym-144-miniapp-cache-headers
status: done
priority: high
type: bug-fix
labels: [infra, web, cache, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T17:50:00Z
start_date: 2026-06-12T17:50:00Z
finish_date: 2026-06-12T17:55:00Z
updated: 2026-06-12T17:55:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-143]
commits: [bd8f938]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-144 — Mini App serves stale bundle after deploy

## Problem
After a deploy, the operator kept seeing the OLD frontend bundle on-device: the
GYM-143-v2 sheet-layout fix was live and verified (headless, realistic iPhone +
Telegram fullscreen insets at 393×852 and 375×667: REPS fully visible, SAVE and
MOVE SET above the nav, no overlap), yet the device showed the v1 layout (REPS
hidden behind SAVE, Cancel top clipped). Root cause: Telegram's in-app webview
caches `index.html` aggressively, and `index.html` references the hashed asset
filenames — so a stale HTML entry keeps loading the old JS for hours.

`apps/web/nginx.conf` long-cached `/assets/` and `/fonts/` as `immutable` (correct,
they are content-hashed) but served `index.html` with NO `Cache-Control`, leaving
caching to the webview's aggressive defaults.

## Solution
Add a `location = /index.html` block sending `Cache-Control: no-store,
must-revalidate` (always). The SPA fallback's internal redirect to `/index.html`
re-enters this exact-match location, so every client-side route's HTML response is
also no-store. Hashed `/assets` and `/fonts` stay immutable — so the bytes still
cache long-term, only the tiny HTML entry revalidates each open. Standard pattern:
immutable hashed assets + never-cached HTML entry.

## Comments

### 2026-06-12T17:55:00Z — fixed at the root (nginx)
The recurring Mini App cache problem the operator flagged ("у нас постоянно
проблемы") is this. Going forward a fresh deploy is picked up on the next open.
The currently-cached client still needs one manual cache-clear / full reopen to
cross over to the no-store header.
