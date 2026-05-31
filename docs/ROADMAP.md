# Gym Platform — Roadmap

> Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Phased execution plan. Each phase lists goal, scope, why-now, dependencies, and where parallel agents/devs can fan out.
> Effort is a rough T-shirt size (S ≈ hours, M ≈ a day or two, L ≈ several days), not a commitment.

Legend: 🔒 security · ⚡ perf · 🏗️ structure · 🔑 keystone · 🚀 feature

---

## Phase 0 — Quick wins & safety net (do first, cheap, high value)
**Goal:** stop the bleeding without touching architecture. Each item is independent and low-risk.

| Item | Type | Effort | Notes |
|------|------|--------|-------|
| Add indexes on `training(user_id, date)`, `training(exercise_id)`, `users(username)` | ⚡ | S | Kills the legacy-site full-scan problem at the source; helps bot analytics too. |
| Remove hardcoded secrets: DB creds in `ci.yaml`, admin `admin/olykov`, default JWT secret, AWS pw in `db.py` | 🔒 | S | Move to CI secrets / env. Rotate exposed creds. |
| Add `.dockerignore` (all build contexts) + root `.env.example` | 🔒 | S | Prevent secret leakage into images; document config. |
| Stop tearing down Postgres/Redis on every deploy (Ansible `state: absent` → only app services) | 🏗️ | S | Removes DB downtime per push. |
| Production builds: `vite build`+static serve, `uvicorn` without `--reload` | 🏗️ | M | Admin services currently run dev servers in prod. |

**Dependencies:** none. **Parallelizable:** yes — each row is an independent agent/PR.
**Exit:** no committed secrets, indexed hot table, deploys don’t bounce the DB.

---

## Phase 1 — Monorepo restructure (no behavior change)
**Goal:** move to the `apps/` + `packages/` + `infra/` layout from ARCHITECTURE §3.2. Pure reorganization; the system behaves identically.

- Move `app/` → `apps/bot/`, `admin_panel/backend` → `apps/api/`, `admin_panel/frontend` → `apps/admin/` (and carve the Mini App into `apps/miniapp/` or keep dual-purpose for now).
- `init.sql` + future migrations → `packages/db/`.
- Compose, Ansible, CI → `infra/` + path-filtered workflows (build only what changed).
- Empty scaffolds for `packages/api-contract`, `packages/shared`.

**Dependencies:** Phase 0 ideally first (so we restructure clean code). **Parallelizable:** low — it’s mechanical moves + import/path fixups, best done in one focused pass.
**Exit:** repo matches target layout; CI green; one `docker compose up` still runs everything.

---

## Phase 2 — Core API consolidation 🔑
**Goal:** make `apps/api` the single DB owner and publish a contract.

- Adopt **Alembic**; capture current schema as the baseline migration; retire hand-run SQL/`db.py`/`import_data.py`.
- Define the **OpenAPI contract** in `packages/api-contract`; generate a Python client (for the bot) and a TS client (for web/admin/miniapp).
- De-duplicate the per-user visibility logic (global/private/hidden muscles & exercises) into one place in the API.
- Unify ID generation (pick one scheme for `training.id`).
- Endpoints to cover everything the bot needs (see Phase 3).

**Dependencies:** Phase 1. **Parallelizable:** medium — contract design is the bottleneck; once endpoints are stubbed, client generation and endpoint implementation fan out.
**Exit:** contract published; API covers all bot+admin data operations; one code path for isolation logic.

---

## Phase 3 — Bot off direct SQL → Core API client 🔑
**Goal:** the bot stops importing `psycopg2`; `handlers.py` and `markups.py` call the generated API client. Also moves blocking DB I/O off the bot’s event loop (the calls become async HTTP).

- Replace `db.*` calls (≈13 methods, including DB-driven keyboard rendering) with API calls.
- Bot needs only an API base URL + service token, not `DB_*` vars.

**Dependencies:** Phase 2 (contract + endpoints). **Parallelizable:** medium — split by handler group (logging flow / muscle-exercise management / analytics keyboards).
**Exit:** bot has no DB driver; only the Core API talks to Postgres.

---

## Phase 4 — Postgres RLS 🔒🔑
**Goal:** DB-enforced per-user isolation.

- Dedicated low-privilege API role; `ENABLE` + `FORCE ROW LEVEL SECURITY` on user-owned tables; policies on `current_setting('app.user_id')`.
- Core API wraps each request in a transaction with `SET LOCAL app.user_id = …`.
- Remove (or keep as defense-in-depth) the now-redundant hand filters.

**Dependencies:** Phase 3 (single owner is a hard prerequisite). **Parallelizable:** low — security-critical, single careful pass + tests.
**Exit:** isolation holds even if an endpoint forgets a `WHERE`.

---

## Phase 5 — Rebuild the website on the Core API ⚡🚀
**Goal:** replace `site_old` with `apps/web` that calls the API — no `pg` in the frontend, cached, indexed, sargable.

- Aggregations live in the API with caching (Redis) + the Phase-0 indexes; remove `SUBSTRING(date::text)` patterns; add pagination.
- Public dashboard / analytics rebuilt; optionally shares components with `apps/miniapp`.

**Dependencies:** Phase 2 (API). Can overlap Phase 3/4. **Parallelizable:** high — a frontend agent builds `apps/web` against the contract while others work on bot/RLS.
**Exit:** the site cannot take down the server by design; old `site_old` deleted.

---

## Phase 6 — Subscriptions (free / paid) 🚀
**Goal:** entitlements across all clients.

- `subscriptions`/`entitlements` domain in the API; tier middleware; gate premium features.
- Payment provider (Telegram Stars and/or Stripe) behind the API.

**Dependencies:** Phases 2–4. **Parallelizable:** medium — billing backend + per-client paywall UI in parallel.

---

## Phase 7 — AI integration 🚀
**Goal:** workout advice, muscle highlights, form tips — server-side behind entitlements.

- AI module in the API; provider via env; rate-limited per tier.
- Clients render advice; mobile shows muscle graphics.

**Dependencies:** Phases 2, 6 (entitlements). **Parallelizable:** medium.

---

## Phase 8 — New clients & domains 🚀
**Goal:** the payoff of the contract.

- `apps/ios` (Swift) against the contract; Android later.
- Calorie-tracker domain in the API + UI in clients (the all-in-one vision).
- ChatGPT/MCP integration: a public/scoped API surface + MCP server so users connect their own agents.

**Dependencies:** Phase 2 (contract) for each. **Parallelizable:** very high — this is where many agents/devs run concurrently, each owning a client or domain against the stable contract.

---

## Phase 9 — Kubernetes (when scale demands it)
**Goal:** independent deploy/scale per service.

- Helm charts in `infra/k8s`; managed Postgres/Redis; ingress + TLS; HPA on stateless services; drop pinned container names/static ports.

**Dependencies:** stable Core API + prod builds (Phases 2, 5). **Trigger:** load/traffic that Compose-on-one-host can’t serve.

---

## Critical path & where parallelism unlocks

```
Phase 0 (parallel quick wins)
        │
   Phase 1 (restructure)
        │
   Phase 2 (Core API + contract)  ◀── the unlock
        ├─────────────┬───────────────┬────────────────┐
   Phase 3 (bot)   Phase 5 (web)   Phase 6 (subs)   Phase 8 (clients)
        │                                              (iOS/Android/MCP,
   Phase 4 (RLS)                                        calorie tracker)
```

**The single most important step is Phase 2.** Before it, work is mostly serial (everything waits on the API). After it, the contract lets many agents/devs build clients and domains **in parallel** — exactly the workflow you want.

---

## Suggested immediate next action
Start with **Phase 0** — it’s cheap, independent, reversible, and the DB index alone removes the root cause of the server-killing site. We can run several Phase-0 items as parallel agents. Say the word and I’ll write a per-item plan (per CLAUDE.md feature workflow) before touching code.
