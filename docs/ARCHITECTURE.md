# Gym Platform — Architecture

> Status: **Proposal for review** · Author: architecture pass 2026-05-31 · Decision: monorepo, single DB-owning Core API.
> This document describes the **target** architecture and the reasoning. Execution is in [ROADMAP.md](ROADMAP.md).

---

## 1. Where we are today (as-built)

Single git repo, deployed as one Docker-Compose stack on one host behind an external reverse-proxy network (`core-infra`).

| # | Component | Path | Stack | Data access |
|---|-----------|------|-------|-------------|
| 1 | Telegram bot | `apps/bot/` | aiogram 3.28 + FastAPI webhook, Redis FSM | **Direct Postgres** (raw psycopg2) |
| 2 | Admin API | `apps/api/` | FastAPI + SQLAlchemy, JWT | Direct Postgres (ORM) |
| 3 | Mini App + Admin UI | `apps/admin/` | React 18 + Vite + Tailwind | Through Admin API (clean) |
| 4 | Legacy website | `site_old/` (deprecated, off) | Next.js 15 + **`pg` in the frontend** | **Frontend → Postgres directly** |
| 5 | Data stores | compose | postgres:16, redis:7 | — |

`src/` = README screenshots only. `db.py` / `import_data.py` / `migrate_user_specific.py` = one-off scripts with hardcoded credentials.

### The root problem

**No single backend owns the database.** Three clients reach into Postgres independently (bot via raw SQL, admin API via ORM, legacy site straight from the frontend). Consequences:

- Per-user isolation is hand-written `WHERE user_id = …` and **duplicated** across the bot (raw SQL) and the admin API (SQLAlchemy) — they have already drifted (training-row IDs are `md5` in the bot vs `uuid4` in the API).
- **No Postgres RLS** — impossible to add cleanly while multiple clients connect as the same role and each re-implements filtering.
- The legacy site’s direct DB access + missing indexes is what pegged CPU/RAM and could take down the host (see §2).
- The bot cannot be split, scaled, or reused by other clients without dragging the schema and `psycopg2` along.

### Other health issues (carried into the roadmap)

- **Monolithic deploy**: one Ansible playbook does `state: absent → present` on the whole stack → Postgres/Redis go down on **every** push to `main`.
- **Dev servers in prod**: admin frontend runs `vite dev`, admin backend runs `uvicorn --reload`.
- **Security**: hardcoded admin `admin/olykov`, default JWT secret fallback, DB password committed in `.github/workflows/ci.yaml`, AWS password in `db.py`, no `.dockerignore`, no root `.env.example`.
- **No migration tooling** (no Alembic); schema is edited by hand; `init.sql` only runs on a fresh volume.
- **Blocking DB I/O** (`psycopg2`) on the bot’s async event loop.
- **No indexes** on `training(user_id, date, muscle_id, exercise_id)` — every analytics query is a full table scan.

---

## 2. Why the legacy site was so expensive (kept as a design lesson)

`site_old/` is the anti-pattern we must never repeat:

1. A `pg` connection pool lives **inside the Next.js app** (`lib/database.ts`) — the website *is* the DB client.
2. `training` has **no indexes** on the filtered/joined/sorted columns → sequential scans.
3. One profile load fires **~5 independent full-scan aggregations**; chart pages add more.
4. Non-sargable predicates (`SUBSTRING(t.date::text …)`) make indexes unusable even if added.
5. Extra diagnostic full-scans on the **empty-data path** (new users = most expensive).
6. No caching anywhere; charts refetch on every mount / dropdown change.

Result: a handful of users or one crawler → dozens of concurrent full scans → 100% CPU + OOM, and because DB and web were co-located, the DB load took the whole machine down.

**The fix is architectural, not a patch:** clients never touch the DB; they call the Core API, which owns indexes, caching, and query governance.

---

## 3. Target architecture

### 3.1 Keystone — one **Core API** that owns the database

Exactly one service holds DB credentials and runs SQL. Every client (bot, Mini App, website, admin, iOS, Android, ChatGPT/MCP) talks to it over HTTPS. This single decision unlocks everything else: RLS, subscriptions, AI, parallel development, independent scaling.

```
                         ┌─────────────────────────────┐
   Telegram  ──────────▶ │  apps/bot (aiogram, thin)    │ ─┐
                         └─────────────────────────────┘  │
   Browser / Mini App ─▶  apps/web / apps/miniapp ────────┤   HTTPS + JWT
   Admins ────────────▶   apps/admin ────────────────────┤   (one token model)
   iOS / Android ─────▶   apps/mobile (future) ──────────┤
   ChatGPT / Claude ──▶   MCP / public API (future) ─────┤
                                                          ▼
                                          ┌───────────────────────────────┐
                                          │  apps/api  ── THE Core API     │
                                          │  FastAPI · owns all SQL        │
                                          │  auth · RLS · billing · AI     │
                                          └───────────────┬───────────────┘
                                                          │ only DB client
                                       ┌──────────────────┴───────────────┐
                                       ▼                                  ▼
                                Postgres (RLS)                       Redis (cache,
                                managed/StatefulSet                  sessions, bot FSM)
```

`apps/api` is already ~60% of this Core API (FastAPI, SQLAlchemy models for all tables, JWT, three Telegram auth flows). We grow it into the single owner rather than start from zero.

### 3.2 Monorepo layout (decided)

One repo, clear package boundaries. Best fit for a small team + many AI agents working in parallel against a **shared contract**.

```
gym-platform/
├── apps/
│   ├── api/            # Core API (FastAPI) — owns the DB. The keystone.
│   ├── bot/            # Telegram bot (aiogram) — thin, calls api via contract client
│   ├── web/            # Public website / dashboard (rebuilt; replaces site_old)
│   ├── miniapp/        # Telegram Mini App (React) — may share code with web
│   ├── admin/          # Admin panel (React)
│   ├── ios/            # future
│   └── android/        # future
├── packages/
│   ├── api-contract/   # OpenAPI spec + generated TS & Python clients  ← parallel-dev enabler
│   ├── db/             # schema, Alembic migrations, RLS policies, seeds
│   └── shared/         # shared types, constants, enums
├── infra/
│   ├── compose/        # docker-compose.{local,prod}.yml
│   ├── ansible/        # deploy automation
│   └── k8s/            # future Helm charts
├── .github/workflows/  # per-app build + path-filtered CI
└── docs/               # this file, ROADMAP.md, ADRs
```

**Why monorepo here:** the API contract is visible to every client in one place; a change to an endpoint + all its consumers lands in one atomic PR; one CI with path filters builds only what changed; agents/devs can own `apps/web` and `apps/bot` simultaneously without cross-repo version juggling. Multi-repo would add contract-sync overhead with no payoff at this team size.

### 3.3 The contract is the parallel-development enabler

`packages/api-contract` holds the OpenAPI spec as the source of truth and generates typed clients (TypeScript for web/miniapp/admin, Python for bot, later Swift/Kotlin). Once the contract exists, **N clients can be built in parallel** against it — each agent/dev codes a client without reading the API’s internals, and breaking changes surface as contract diffs in review. This is what makes “many agents on different clients” actually work.

---

## 4. Cross-cutting concerns (all live in / are enforced by the Core API)

### 4.1 Row-Level Security (RLS)
Data model is already RLS-ready (clean `user_id` / `created_by` ownership). To enable:
1. Create a dedicated low-privilege DB role for the API (not the owner/superuser).
2. `ALTER TABLE … ENABLE ROW LEVEL SECURITY; FORCE ROW LEVEL SECURITY;` on user-owned tables.
3. Policies keyed on a request-scoped GUC, e.g. `current_setting('app.user_id')`.
4. The Core API runs each request in a transaction that begins with `SET LOCAL app.user_id = <authenticated id>`.
5. Hand-written `WHERE user_id = …` filters are then removed (defense-in-depth optional) — the DB enforces isolation centrally. **Requires the single-owner API first.**

### 4.2 Unified auth
One token model issued by the Core API. Identity providers feed into it: Telegram (bot identity / Mini App `initData` / Login Widget), later Sign in with Apple / Google for mobile, and scoped API keys for ChatGPT/MCP. Removes the hardcoded admin creds and the three parallel JWT paths.

### 4.3 Subscriptions (free / paid)
A `subscriptions` / `entitlements` domain in the Core API; tier checked in middleware and surfaced to clients. Payment provider pluggable (Telegram Stars and/or Stripe). Entitlements gate premium features (AI advice, advanced analytics, calorie tracker) uniformly across all clients.

### 4.4 AI
An AI module/service behind the Core API (workout advice, muscle-group highlights, form tips). Model provider via env (Anthropic/OpenAI). Never called directly from clients — keeps keys server-side and lets entitlements/limits apply.

### 4.5 Future domains
Calorie tracker = another bounded domain in the Core API + its UI in the clients. Same pattern: domain logic in the API, thin clients.

### 4.6 Observability
Structured logs (already JSON in the bot), request tracing, and per-service health checks become meaningful once services are split and independently deployed.

---

## 5. Deployment evolution: Compose now → Kubernetes later

**Now (Compose, hardened):**
- Split deploy so a single service can ship without nuking the stack; **stop tearing down Postgres/Redis on every deploy** (don’t `state: absent` stateful services; or externalize them).
- **Production builds**: `vite build` + static serve via nginx/caddy; `uvicorn` without `--reload`; multi-stage Dockerfiles (the `site_old` Dockerfile is the only good example today).
- Add `.dockerignore` and a root `.env.example`; move all secrets to CI secrets / Ansible Vault.

**Later (Kubernetes, when scale demands):**
- Each app a `Deployment` + `Service`; ingress for routing/TLS (replaces the external `core-infra` reverse proxy).
- Postgres managed (RDS/Cloud SQL) or a carefully-run `StatefulSet`; Redis managed.
- HPA on the stateless services (api, web, bot); the contract + statelessness make horizontal scaling safe.
- Drop pinned `container_name`/static host ports (they block replicas today).

The component boundaries are already clean, so the build side is split-ready; the **deploy layer** is the real work.

---

## 6. Decisions captured (ADR-style summary)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo strategy | **Monorepo** with `apps/` + `packages/` | Shared contract, atomic cross-client PRs, parallel agents/devs, one CI. |
| DB ownership | **Single Core API owns all SQL** | Unblocks RLS, subscriptions, AI, scaling, client reuse. |
| Core API seed | Grow `apps/api` | Already ~60% there (auth, models, schemas). |
| Parallel-dev mechanism | `packages/api-contract` (OpenAPI + generated clients) | Clients built independently against a typed contract. |
| Migrations | Adopt **Alembic** | Replace hand-run SQL; versioned schema. |
| Isolation | **Postgres RLS** after single-owner API | DB-enforced, not per-client hand-filtering. |
| Orchestration | **Compose now, k8s later** | Boundaries ready; harden deploy first. |

See [ROADMAP.md](ROADMAP.md) for the phased execution plan.
