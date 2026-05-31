---
schema_version: 1
id: GYM-18
title: "Bot 502 after deploy — reverse proxy stale upstream (DNS resolver fix)"
slug: gym-18-webhook-502-proxy-stale-upstream
status: done
priority: high
type: bug-fix
labels: [phase-0, infra, incident]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T19:30:00Z
start_date: 2026-05-31T19:30:00Z
finish_date: 2026-05-31T19:45:00Z
updated: 2026-05-31T19:45:00Z
epic: phase-0
depends_on: []
blocks: []
related: [GYM-6, GYM-7]
commits: ["4d15143"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-18 — Bot 502 after deploy (reverse proxy stale upstream)

## Problem
After a deploy recreated the bot container (new IP on the core-infra network), Telegram webhook
deliveries returned `502 Bad Gateway` (getWebhookInfo: pending_update_count > 0, last_error
"Wrong response from the webhook: 502"). The bot itself was healthy (local `POST /webhook` -> 401).
Root cause: the core-infra nginx vhost used `proxy_pass http://gymbot_backend:5400;`, which nginx
resolves ONCE at start/reload and caches; after container recreation the cached IP was stale.
Surfaced during GYM-6 verification; recurs on every deploy until a manual `nginx -s reload`.

## Solution
Make nginx re-resolve the upstream at request time via Docker's embedded DNS:
- `resolver 127.0.0.11 valid=10s ipv6=off;`
- `set $gymbot_upstream gymbot_backend;` + `proxy_pass http://$gymbot_upstream:5400;` (variable
  forces per-request resolution; TTL 10s).
Applied to the live core-infra proxy (`nginx -t` + `nginx -s reload`); pending updates drained to 0,
bot responsive. Future deploys self-heal within ~10s — no manual reload needed.

The live proxy is managed outside this repo (core-infra host); a reference copy of the corrected
vhost is kept at infra/nginx/gymbot.olykov.com.conf.

## Comments

### 2026-05-31T19:45:00Z — done
Operator applied the resolver+variable fix on the core-infra nginx and confirmed getWebhookInfo
pending=0, bot working. Reference config committed (4d15143). Our ansible deploy no longer needs a
manual proxy reload.
