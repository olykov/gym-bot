# Gym Platform — Agent & Developer Guide

This is the source-of-truth guide for working in this repo. It OVERRIDES default behavior.
For the bigger picture and the rebuild plan, read:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — target architecture and decisions
- [docs/ROADMAP.md](docs/ROADMAP.md) — phased execution plan
- [docs/agentic-plan.md](docs/agentic-plan.md) — the subagent setup we plan to add
- [.claude/skills/telegram-design/](.claude/skills/telegram-design/) — Telegram UI/keyboard design skill

---

## Project Overview

A Telegram gym training-logger that is being grown into a multi-client platform.

| Component | Path | Stack | Status |
|-----------|------|-------|--------|
| Telegram bot | `apps/bot/` | aiogram 3.28 + FastAPI webhook, Redis FSM | live (prod) |
| Admin/Core API | `apps/api/` | FastAPI + SQLAlchemy, JWT | live |
| Mini App + Admin UI | `apps/admin/` | React 18 + Vite + Tailwind | live (this is the in-Telegram Mini App) |
| Data stores | compose | postgres:16, redis:7 | live |
| Legacy website | `site_old/` | Next.js (direct DB access) | deprecated, off — to be rebuilt |

Layout: `apps/` (services), `packages/` (db schema, future api-contract & shared), `infra/` (ansible, future k8s), `scripts/` (one-off: db.py, import_data.py), `docs/`. `src/` is just README images.

## Architecture Invariants (do NOT regress)

These were hard-won in the webhook migration and must stay:
- **Bot transport**: webhook only (`apps/bot/main_webhook.py`), with `X-Telegram-Bot-Api-Secret-Token` validation. Not polling.
- **State**: aiogram FSM backed by **Redis** (`RedisStorage`). ❌ Never an in-memory dict for user state.
- **DB access**: **connection pool** (`ThreadedConnectionPool`) via `get_cursor()` context manager. ❌ Never a single global connection/cursor.

Known debt (tracked in [docs/ROADMAP.md](docs/ROADMAP.md)) — be aware, don't pretend it's solved:
- DB calls are **synchronous psycopg2 on the async event loop** (HP-1, still open). The bot is not yet truly async at the DB layer.
- **No Postgres RLS**; per-user isolation is hand-written `WHERE user_id` and duplicated across the bot and the admin API.
- **No single backend owns the DB** — bot and admin API are two independent DB clients.

## How to Run / Build / Deploy

- **Local**: `docker compose -f docker-compose.local.yaml up` (builds locally, bind-mounts source).
- **Prod deploy**: push to `main` → GitHub Actions **"Build and Deploy"** (~3 min: builds bot/admin-backend/admin-frontend images, then one Ansible playbook brings the stack up on one host). Watch with `gh run list --limit 1` then `gh run view <id>`.
- **Search**: use `rg` (ripgrep), not `grep`/`find`.

---

# AGENT BEHAVIOR RULE: Structured Feature Implementation

## MANDATORY WORKFLOW FOR ALL FEATURE REQUESTS

### 1. Requirement Analysis Phase
- **ALWAYS** read and understand the complete user request.
- **ALWAYS** identify current state vs desired state.
- **ALWAYS** break the request into specific, actionable components.
- **ALWAYS** apply **KISS** — choose simple solutions over complex ones.
- **ALWAYS** apply **YAGNI** — implement only what's needed now, not anticipated future needs.
- **NEVER** start implementation without explicit user approval.

### 2. Comprehensive Planning Phase
When the user requests new functionality, present a plan in this shape:

```
## Plan: [Feature Name]

### Current State:
[How it works now]

### Desired State:
[How it should work after]

### Implementation Plan:
1. [Specific technical step]
2. ...

### Technical Details:
[Code snippets, DB changes, file modifications]
- File Structure: files under 500 lines, functions under 50 lines
- Type Hints: complete type annotations
- Error Handling: fail-fast validation, specific exceptions
- Search: use `rg`

### User Experience Impact:
[Before/after with real user flows]

### Safety Considerations:
[Error handling, backward compatibility, edge cases]

### Benefits:
[Clear value]

### Edge Cases Handled:
[Specific scenarios]
```

Then wait for approval:
- **NEVER** proceed without the user approving the plan.
- End with: "**Please approve this plan and I'll proceed with implementation!**"
- Ask: "Is this exactly what you want?"

### 3. Implementation Phase
Once approved:

**A. Track progress** — keep a structured todo list; mark items done immediately as you finish them.

**B. Follow implementation order:**
1. Database changes first (if needed).
2. Core logic updates (single responsibility).
3. Handler/controller updates (functions under 50 lines).
4. UI/display updates (consistent naming).
5. Error handling & validation (fail-fast, specific exceptions).
6. Type hints & docstrings.
7. Tests for critical paths (see Testing — be honest about what exists).
8. Code quality pass.

**C. Show before/after** for every user-facing change:
```
### Before: [current]
### After:  [new]
```

### 4. Error Handling & Edge Cases
Always consider:
- **Backward compatibility**: never break existing functionality; handle missing data gracefully; new users with no data get a sensible experience.
- **UX scenarios**: new users (no data), experienced users (existing data), invalid/missing data, navigation (back buttons, context preservation).
- **Technical safety**: DB errors → graceful fallback; missing data → safe defaults; invalid states → validation.

Required pattern for DB operations:
```python
try:
    result = db.save_training_data(...)
    if not result["success"]:
        logger.error(f"Save failed: {result.get('error')}")
        await message.reply("❌ Error saving data. Please try again.")
        return
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    await message.reply("❌ An error occurred. Please contact support.")
    return
```
> Note: DB methods are currently **synchronous** (psycopg2). Do not write `await db.method()` until the DB layer is actually async (HP-1).

### 5. Documentation Requirements
- Update README.md for user-facing features (usage examples, UX changes).
- Google-style docstrings for all public functions; type hints in every signature.
- `# Reason:` comments for non-obvious logic.

### 6. Communication Patterns
- **Planning**: clear structure, concrete examples (not abstractions), ask for approval.
- **Implementation**: update todos in real time; explain what each change accomplishes; show before/after.
- **Completion**: summarize what was implemented, the full UX flow, and confirm requirements were met.

### 7. Quality Assurance Checklist
Before marking a feature complete:
- [ ] All requirements addressed
- [ ] Backward compatibility maintained
- [ ] Error handling implemented
- [ ] Edge cases covered
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Follows existing patterns
- [ ] Files under 500 lines, functions under 50 lines
- [ ] Complete type hints
- [ ] Google-style docstrings on public functions
- [ ] `rg` used for search
- [ ] Lint/format/type-check pass **if the tooling is configured** (see Tooling)

### 8. Mandatory Phrases
- Planning: "**Please approve this plan and I'll proceed with implementation!**" / "Is this exactly what you want?"
- Implementation: "Perfect! Let's implement [feature]" / "I'll start by [action]"
- Completion: "## ✅ [Feature] — Implementation Complete!"

### 9. Development Principles
- **KISS**, **YAGNI**, **Single Responsibility**, **Open/Closed**, **Dependency Inversion**.
- **Size limits**: files < 500 lines, functions < 50 lines, classes < 100 lines, line length ≤ 100.
- **Type hints** on all functions; **Google-style docstrings** on public ones.
- **Fail fast**: validate early, raise specific exceptions; use context managers for resources; structured logging with context.

> Reality check: `app/modules/handlers.py` is currently ~714 lines (over the limit). Don't grow it further — split when you touch it.

---

## Database & Data Standards

- **Access**: only through the pooled `get_cursor()` context manager (auto-commit on success, auto-rollback on error). Parameterized queries only (`%s`).
- **Going-forward PK convention**: entity-specific primary keys (`{entity}_id`) and FKs (`{referenced_entity}_id`).
  - ⚠️ Legacy reality: existing tables use a bare `id` PK (and `exercises.muscle` instead of `muscle_id`). Don't "fix" live columns ad-hoc — schema changes go through a migration (Alembic, see ROADMAP).
- **Field naming**: `created_at`, `is_active`, etc.
- **Isolation**: today it's hand-written `WHERE user_id = %s` plus `is_global`/`created_by` ownership. Real Postgres RLS is a roadmap item, not done — see [docs/ROADMAP.md](docs/ROADMAP.md) Phase 4.
- **Migrations**: there is no migration framework yet; `init.sql` runs only on a fresh volume. Adopting Alembic is planned.

## Testing

Be honest about the current state:
- **There is no test suite** (no `tests/`, no pytest config) at the time of writing. Do not claim to have run tests that don't exist.
- For now, validate with: `python3 -m py_compile <files>`, targeted logic checks, and a **manual smoke test** (send a message to the bot, verify the reply, check logs, verify the DB row).
- When a real suite is added, use **pytest** (unit + integration) and state actual results.

## Tooling

- **Current**: Python deps via `pip` + `requirements.txt`; Docker images via the CI pipeline. No linter/formatter/type-checker is configured yet.
- **Target** (roadmap): `uv` for package management, `ruff` for lint+format, `mypy` for type checking. Until these are configured in the repo, don't assert they passed — say "not configured yet."

## Commit Message Standards

**NEVER include**:
- ❌ Emojis in commit messages
- ❌ "Co-Authored-By" lines
- ❌ "Generated with Claude Code" / any AI attribution

**ALWAYS**:
- ✅ Clean, professional, present-tense messages
- ✅ Title ≤ ~10 words unless genuinely complex

Single-line is preferred:
```
Add webhook mode with Redis and production config
Highlight personal-record weight and reps buttons in green
```
Multi-line when needed:
```
Brief description

- Detailed change 1
- Detailed change 2
```

Commit/push only when the user asks. Direct commits to `main` are the norm here (deploy triggers off `main`).

---

## Reference & Pointers

| Topic | Location |
|-------|----------|
| Target architecture & decisions | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Phased plan | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Subagent plan | [docs/agentic-plan.md](docs/agentic-plan.md) |
| Telegram UI design skill | [.claude/skills/telegram-design/](.claude/skills/telegram-design/) |
| Bot entry point | [apps/bot/main_webhook.py](apps/bot/main_webhook.py) |
| Bot handlers | [apps/bot/modules/handlers.py](apps/bot/modules/handlers.py) |
| DB layer | [apps/bot/modules/postgres.py](apps/bot/modules/postgres.py) |
| FSM states | [apps/bot/modules/states.py](apps/bot/modules/states.py) |
| Admin/Core API | [apps/api/](apps/api/) |
| DB schema bootstrap | [packages/db/init.sql](packages/db/init.sql) |

> `TODO.md` and `IMPLEMENTATION.md` exist but are **stale** (they describe the already-completed webhook migration). Treat [docs/ROADMAP.md](docs/ROADMAP.md) as the current plan, not those files.
