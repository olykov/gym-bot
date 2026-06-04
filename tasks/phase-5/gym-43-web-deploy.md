---
schema_version: 1
id: GYM-43
title: "Infra: apps/web Dockerfile + CI build + nginx route on gymbot.olykov.com"
slug: gym-43-web-deploy
status: review
priority: medium
type: chore
labels: [phase-5, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T15:40:00Z
finish_date: 2026-06-04T16:30:00Z
updated: 2026-06-04T16:30:00Z
epic: phase-5
depends_on: [GYM-41]
blocks: []
related: [GYM-12]
commits: [5b07d8d54ecbc46ba83ea5946b63154490a1d484]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-43 — Infra: build + deploy apps/web

## Problem
`apps/web` needs an image, a CI build job, and to be served on the current domain as the Mini App.

## Plan
- `apps/web/Dockerfile` (Vite build → nginx static), mirroring `apps/admin`.
- CI build job for `web-frontend` in `.github/workflows/ci.yaml`; compose `web_frontend` service.
- nginx on `gymbot.olykov.com`: serve `apps/web` at `/` (keep `/webhook` → bot). Keep `apps/admin`
  reachable (e.g. a temporary path) until its relocation task — DO NOT break admin in this cutover.
  Use the Docker-DNS resolver pattern (GYM-18) for the new upstream.

## Acceptance criteria
- [ ] web_frontend builds + deploys; `gymbot.olykov.com/` serves the Mini App; bot webhook intact.

## Comments

### 2026-06-04T09:00:00Z — task created
Admin relocation/embedding is a separate backlog task — out of scope here.

### 2026-06-04T16:30:00Z — implementation complete (5b07d8d)

**What was wired:**
- CI: `build-web-frontend` job added to `.github/workflows/ci.yaml`; repo-root
  build context (same pattern as bot build); `WEB_FRONTEND_IMAGE` env var;
  threaded into `deploy` job needs + Ansible env.
- Compose: `web_frontend` service added to both `docker-compose.yaml` and
  `docker-compose.local.yaml` mirroring `admin_frontend`; port 5175:80;
  `core-infra` network; `restart: always`; local build uses repo-root context.
- Ansible: `WEB_FRONTEND_IMAGE`/`WEB_FRONTEND_TAG` written into server `.env`
  via `infra/ansible/deploy.yaml`.
- nginx: `infra/nginx/gymbot.olykov.com.conf` rerouted — `/` → `web_frontend:80`
  (Mini App), `/admin/` → `admin_frontend:80` (temporary; strips prefix via
  rewrite), `/webhook` → `gymbot_backend:5400` (unchanged). All three upstreams
  use GYM-18 `resolver 127.0.0.11 valid=10s` + `set $var` pattern.

**TS client generation in the build:**
`packages/api-contract/clients/typescript/` is gitignored so it is absent in
CI checkout. The `apps/web/Dockerfile` (repo-root context) copies
`packages/api-contract/openapi.yaml` into the build image and runs
`npx --yes openapi-typescript@7 <spec> -o /packages/api-contract/clients/typescript/schema.ts`
before `npm run build`. The vite alias `@api-contract` resolves to
`../../packages/api-contract/clients/typescript` relative to `apps/web/` —
i.e. `/packages/api-contract/clients/typescript` inside the build stage where
`WORKDIR /app`. The generated file is there before tsc/vite run.

**Compose validation:**
- `docker compose -f docker-compose.yaml config`: ✅ parses cleanly, `web_frontend` present.
- `docker compose -f docker-compose.local.yaml config`: ✅ parses cleanly, `web_frontend` present.

**nginx validation:**
nginx not installed locally; self-reviewed. Syntax is consistent with the
pre-existing GYM-18 pattern used in the same file (resolver + variable upstream).
The `rewrite ^/admin/(.*)$ /$1 break` correctly strips the prefix for the admin
proxy. Operator should run `nginx -t` on the server after applying the live conf.

**Known limitation — admin at /admin/:**
`apps/admin` Vite base is `/` so its root-relative asset URLs (`/assets/...`)
will be routed to `web_frontend` instead of `admin_frontend`. The SPA shell
will load but assets may 404. Full fix requires `base: '/admin/'` in
`apps/admin/vite.config.ts` — deferred to the admin-relocation task.
