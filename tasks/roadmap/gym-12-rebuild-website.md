---
schema_version: 1
id: GYM-12
title: "Phase 5: Client Telegram Mini App (apps/web) on the Core API"
slug: gym-12-rebuild-website
status: review
priority: medium
type: feature
labels: [phase-5, frontend]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-06-04T10:00:00Z
finish_date: null
updated: 2026-06-04T16:40:00Z
epic: roadmap
depends_on: [GYM-9, GYM-11]
blocks: []
related: [GYM-4, GYM-38, GYM-39, GYM-40, GYM-41, GYM-42, GYM-43, GYM-44, GYM-45]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-12 — Phase 5: Client Telegram Mini App (apps/web) on the Core API

## Problem
`site_old` (Next.js) hit Postgres directly with full-scan `GROUP BY/DATE_TRUNC` aggregations and no
caching — it could take down the server. It is off. We need the analytics client back, but it cannot
recur by design.

## Intent (corrected with the operator, 2026-06-04)
- `apps/web` is **the client Telegram Mini App**, served on the **current domain**
  (`gymbot.olykov.com`). It opens **inside Telegram on phones (~99.9%).** It progressively replaces
  `apps/admin` as the Mini App.
- The **admin panel relocating** to its own domain / being embedded later is **BACKLOG — out of
  scope here. Do not plan for it now.**
- **Mobile-first is the law.** Desktop works but is secondary.
- Auth via Telegram **WebApp initData** (Core API `verify_telegram_webapp_auth` already exists) → JWT;
  RLS (GYM-11) scopes data per-user automatically, fail-closed. No Login Widget, no new subdomain.

## Plan (MVP first — approved scope)
Thin React+Vite+TS Mini App against the Core API (generated TS client), no pg in the frontend.
Heavy aggregations live in the API: **sargable, on indexes, paginated, Redis-cached (short TTL).**

**v1 (MVP):** Telegram login → JWT · Dashboard (activity-grid + summary: exercises/sets/PRs/streak)
· Exercise progress chart (muscle→exercise, weight/reps over time, ECharts).
**Deferred:** weekly/yearly muscle-sets distribution · profile.

### Design system (binding) — see `docs/frontend-spec.md`
Stable, consistent, mobile-first shell: **fixed header + fixed bottom-nav (always visible) + one
content container at a single max-width**, Telegram-theme tokens (light+dark), spacing scale,
safe-area insets. Distinctive aesthetics in the details, disciplined consistency in the structure.
Owned by the **`frontend-design-engineer`** agent, which is **mandated to invoke the `frontend-design`
plugin (skill)** on every UI task and obey `docs/frontend-spec.md`.

### New API endpoints (RLS-scoped, Redis-cached)
| Endpoint | Purpose | Sargable shape |
|---|---|---|
| `GET /analytics/activity?from&to` | activity grid | `WHERE user_id=? AND date BETWEEN ? AND ? GROUP BY date::date` |
| `GET /analytics/summary` | 4 dashboard numbers | aggregates by user_id |
| `GET /analytics/exercise-progress?muscle&exercise` | weight/reps series | indexed, shaped for ECharts |

### Decomposition
- **GYM-38** (api-contract-guardian) — 3 analytics endpoints in OpenAPI + regen TS & python clients.
- **GYM-39** (core-api-engineer) — implement endpoints (sargable, via get_principal/RLS) + Redis cache util.
- **GYM-40** (infra-engineer) — `REDIS_URL` for admin_backend (bot already uses redis).
- **GYM-41** (frontend-design-engineer) — `apps/web` scaffold + AppShell + tokens + Telegram SDK + auth (design-led, frontend-design plugin mandatory).
- **GYM-42** (frontend-design-engineer) — MVP pages (dashboard activity-grid + summary, exercise progress) on the shell + TS client + TanStack Query.
- **GYM-43** (infra-engineer) — `apps/web` Dockerfile + CI build job + nginx route on `gymbot.olykov.com` (web at `/`; admin relocation is backlog, don't break admin in the cutover).

### Operator decisions (not blockers)
- nginx cutover: serve `apps/web` at `/` on `gymbot.olykov.com`; keep `apps/admin` reachable until
  its relocation task. Exact swap order = GYM-43.

## Comments

### 2026-05-31T16:00:00Z — task created
The heavy site cannot recur by design.

### 2026-06-04T09:00:00Z — re-scoped: it's the client Mini App, mobile-first, design-system-first
Operator clarified apps/web is the in-Telegram client app on the CURRENT domain (admin moves later,
backlog). Added: mobile-first law, binding design system (docs/frontend-spec.md), a dedicated
`frontend-design-engineer` agent mandated to use the `frontend-design` plugin, Redis cache for the
aggregations. MVP scope approved (dashboard + exercise progress + login). Sub-tasks GYM-38..43.
Plan to be refined by the design agent via the plugin, then operator-approved before start.
