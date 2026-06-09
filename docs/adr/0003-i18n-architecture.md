# ADR 0003 — i18n architecture: one locale foundation, two delivery channels

- Status: accepted (operator approved 2026-06-10)
- Date: 2026-06-10
- Relates to: ADR 0001 (reference + overrides), ADR 0002 (canonical layer; `exercise_alias.lang` shipped in migration 0006)
- Epics/tasks: i18n-foundation (GYM-108), tax-i18n (GYM-93 search, GYM-94 dropdown, GYM-92 exercise seed), ui-i18n (GYM-109)

## Context
The app must localize to the user's Telegram language (a couple of languages to start: `en`, `ru`).
Three things need translating: **UI strings** (chrome — buttons, headings, toasts), **muscle names**
(a fixed set of 8 global muscles), and **exercise names** (122 global, user-extensible, server-searched).
Question raised: is this one task on a shared foundation, or separate tasks?

## Decision
**One shared foundation; two distinct delivery channels.** They are complementary, not the same task —
forcing them into one mechanism would be wrong in both directions.

### Shared foundation (`i18n-foundation`)
1. **Locale resolution** — resolve the active locale from Telegram `language_code`
   (`WebApp.initDataUnsafe.user.language_code`) to a supported locale, with a fallback chain
   (unknown → `en`). One implementation, consumed by BOTH channels: the frontend picks its string
   catalog by it AND passes `lang` to the search API; the API filters `exercise_alias.lang` by it.
2. **Supported-locales registry** — a single source of truth for which languages exist (`en`, `ru`)
   and their ISO-639-1 codes, so UI catalogs and DB seeds never drift apart.

### Channel A — UI strings + muscle names → **frontend string catalog**
- Static, developer-authored, finite, NOT user-extensible, NOT searched server-side.
- Lives in the frontend as per-locale catalogs (`en.json` / `ru.json`, a lightweight i18n lib).
- **The 8 fixed muscles belong here** — they are a small fixed label set, so a `muscle_alias` DB table
  is NOT needed and is dropped from scope. The API keeps returning canonical muscle id/name; the
  frontend maps to the localized label.
- Updated by a frontend deploy. Owned by `ui-i18n` (GYM-109).

### Channel B — exercise names → **DB aliases + search API**
- Dynamic, user-extensible, fuzzy-searched on the server.
- Lives in `exercise_alias` (`canonical_id`, `alias_name`, generated `name_key`, `lang`) — already on
  prod (migration 0006). Search ranks: exact `name_key` → prefix → alias (lang-aware) → `pg_trgm` fuzzy.
- Owned by `tax-i18n`: GYM-93 (search API + `pg_trgm` enable, migration 0007), GYM-94 (add-exercise
  search-and-pick dropdown), GYM-92 (RU exercise-alias seed, migration). EN aliases are unnecessary —
  the canonical name is already English and already searchable via `name_key`.

### Dividing line (how to decide where a new translatable thing goes)
> **Fixed + small + code-coupled → frontend catalog. Dynamic + searched + user-data → DB aliases.**

## Consequences
- `muscle_alias` is never built (muscles localize via the frontend catalog). Simpler than the earlier plan.
- The foundation is a small prerequisite that unblocks both channels and keeps locale codes consistent.
- `ui-i18n` (GYM-109) is a sizable but self-contained frontend refactor (extract hardcoded strings) —
  scheduled as its own wave; it does not block the exercise-search work.
- Recommended order: foundation → exercise-search (GYM-93 → GYM-94) → ui-i18n (GYM-109); the exercise
  RU seed (GYM-92) rides alongside the search work.
- Adding a third language later = one registry entry + one catalog file + one alias-seed pass. No schema change.
