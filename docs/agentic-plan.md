# Agentic Plan — project subagents

> Status: **plan** (not yet created). Captures the subagent setup agreed on 2026-05-31.
> Create these **after the monorepo restructure** ([docs/ROADMAP.md](ROADMAP.md) Phase 1), because their scopes reference `apps/` and `packages/` which don't exist yet.
> Exception: **`security-auditor`** is useful on the current code and can be created now.

## How Claude Code subagents work

- Defined as `.claude/agents/<name>.md` (project-level, **committed** so people + AI share one set) or `~/.claude/agents/` (personal).
- Frontmatter: `name`, `description` (written as "use when…" — this drives automatic delegation), `tools` (least privilege), `model` (tier the cost).
- Each subagent runs in its **own context window** → keeps the main thread clean and lets many run in parallel.

## Principles for this project

- **One agent = one responsibility along an architectural seam** (the contract, the DB, a client, infra) — NOT generic roles. "backend + frontend" is too coarse: it misses the contract owner and the reviewer, and bundles unrelated scopes.
- **Least-privilege tools**: a reviewer is read-only; a migration steward gets DB + code but nothing else.
- **Builder + reviewer split**: pair builders with a separate `security-auditor` for adversarial review.
- **Model tiering**: deep/critical work on `opus`, routine build work on `sonnet`, cheap mechanical checks on `haiku`.
- **Crystal-clear scope**: every agent file states what it MAY touch, what it MUST NOT, and embeds a short operating-standards block (KISS, YAGNI, the project invariants) like a scoped CLAUDE.md.
- **Commit them** in `.claude/agents/` (the `.claude/skills/` exception in `.gitignore` already tracks skills; add agents the same way).

## Roster

| Agent | Seam / scope | Tools | Model |
|-------|--------------|-------|-------|
| `api-contract-guardian` | `packages/api-contract` (OpenAPI spec + generated clients); gate for cross-client changes | Read, Grep, Glob, Edit, Write, Bash | opus |
| `core-api-engineer` | `apps/api` (FastAPI endpoints, business logic) | Read, Grep, Glob, Edit, Write, Bash | sonnet |
| `db-migration-steward` | `packages/db` (Alembic migrations, schema, RLS policies) | Read, Grep, Glob, Edit, Write, Bash | opus |
| `bot-engineer` | `apps/bot` (aiogram, Telegram UX); uses the `telegram-design` skill | Read, Grep, Glob, Edit, Write, Bash | sonnet |
| `client-frontend-engineer` | `apps/web`, `apps/miniapp`, `apps/admin` (React/Vite against the contract) | Read, Grep, Glob, Edit, Write, Bash | sonnet |
| `security-auditor` | read-only reviewer across the repo | Read, Grep, Glob, Bash (read-only) | opus |
| `infra-engineer` | `infra/` (compose, k8s, CI, ansible) | Read, Grep, Glob, Edit, Write, Bash | sonnet |

## Shared operating standards (every agent embeds this)

- **KISS** / **YAGNI** — simplest thing that works; only what's needed now.
- Respect the **Architecture Invariants** in [../CLAUDE.md](../CLAUDE.md) (webhook+Redis FSM+pool; no direct-DB-from-clients in the target).
- Files < 500 lines, functions < 50 lines; type hints + Google-style docstrings.
- `rg` for search; parameterized SQL only; structured logging.
- Plan-before-implement + explicit approval (per CLAUDE.md workflow).
- Commits: no emojis, no AI attribution (per CLAUDE.md).

## Per-agent scope (allowed / forbidden)

### api-contract-guardian
- **Allowed**: edit the OpenAPI spec, regenerate TS/Python clients, review any PR that changes endpoints or schemas.
- **Forbidden**: changing endpoint *implementations* or DB code; making breaking contract changes without flagging every affected client.
- **Extra standard**: the contract is the source of truth — a change here means clients must be regenerated in the same change.

### core-api-engineer
- **Allowed**: implement/modify endpoints, services, auth, business logic in `apps/api`.
- **Forbidden**: hand-editing live DB schema (goes through `db-migration-steward`); embedding secrets; bypassing the contract.
- **Extra standard**: `apps/api` is the ONLY service that owns SQL; keep isolation logic in one place (no per-client duplication).

### db-migration-steward
- **Allowed**: author Alembic migrations, schema changes, RLS policies in `packages/db`.
- **Forbidden**: destructive migrations without an explicit reviewed plan; touching app/business code.
- **Extra standard**: every schema change is a versioned migration; RLS = dedicated low-privilege role + per-request `SET LOCAL app.user_id`.

### bot-engineer
- **Allowed**: aiogram handlers, FSM flows, keyboards, Telegram UX in `apps/bot`.
- **Forbidden**: importing a DB driver / writing SQL (the bot calls the Core API via the generated client); regressing webhook/Redis-FSM/signature invariants.
- **Extra standard**: use the `telegram-design` skill for keyboards/colors; keep `callback_data` machine-stable.

### client-frontend-engineer
- **Allowed**: React/Vite UI in `apps/web`, `apps/miniapp`, `apps/admin`, calling the API via the generated client.
- **Forbidden**: ❌ any direct DB access from the frontend (the `site_old` anti-pattern); embedding DB credentials.
- **Extra standard**: data only through the API; cache/paginate; never recompute heavy aggregates client-side.

### security-auditor (can exist now)
- **Allowed**: read-only review; flag hardcoded secrets, missing RLS, SQL injection, secret leakage into images, broken auth/role gates.
- **Forbidden**: editing code (it reports; humans/other agents fix).
- **Extra standard**: default to skeptical; cite `file:line`; prioritize by blast radius.

### infra-engineer
- **Allowed**: `infra/` — compose, Dockerfiles, CI, ansible, future k8s.
- **Forbidden**: committing secrets; coupling services with hardcoded hostnames that block independent deploy.
- **Extra standard**: production builds (no dev servers in prod); don't tear down stateful services on every deploy.

## Agent file template

```markdown
---
name: <agent-name>
description: Use when <clear trigger>. Owns <scope>. Does NOT touch <forbidden>.
tools: Read, Grep, Glob, Edit, Write, Bash
model: sonnet
---

# <Agent Name>

## Scope
- Allowed: ...
- Forbidden: ...

## Operating standards
- KISS, YAGNI, single responsibility.
- <scope-specific rules>
- Respect Architecture Invariants in ../../CLAUDE.md.
- Plan-before-implement + approval; commits without emoji/AI attribution.
```
