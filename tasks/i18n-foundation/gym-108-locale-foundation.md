---
schema_version: 1
id: GYM-108
title: "i18n foundation: resolve Telegram language_code → supported locale + locales registry"
slug: gym-108-locale-foundation
status: done
priority: high
type: feature
labels: [i18n, frontend, foundation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T01:00:00Z
start_date: 2026-06-10T01:00:00Z
finish_date: 2026-06-10T00:00:00Z
updated: 2026-06-10T01:00:00Z
epic: i18n-foundation
depends_on: []
blocks: [GYM-92, GYM-93, GYM-94, GYM-109]
related: []
commits: [c957b76]
tests: []
design_reports: ["docs/adr/0003-i18n-architecture.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-108 — i18n foundation: locale resolution + registry

## Problem
The app has no locale concept. Both i18n channels (UI-string catalog and exercise-alias search) need a
single, shared answer to "what language is this user?" derived from Telegram, and a single registry of
supported languages so catalogs and seeds never drift. See [ADR 0003](../../docs/adr/0003-i18n-architecture.md).

## Solution
Frontend-only foundation (no API change here; the API `lang` param arrives with GYM-93):
1. **Supported-locales registry** — one shared const: `SUPPORTED_LOCALES = ['en','ru']`, default `en`,
   ISO-639-1 codes. Single source of truth.
2. **Locale resolution** — read `WebApp.initDataUnsafe.user.language_code` (in `apps/web/src/telegram/
   webapp.ts`), normalize (`ru-RU` → `ru`), map to a supported locale with fallback to `en`. Expose a
   small `useLocale()` hook / `getLocale()` util for the rest of the app.

## Acceptance criteria
- [x] `getLocale()` returns a supported locale from `language_code`, `en` for unknown/missing.
- [x] Registry is the only place that lists supported languages.
- [x] `npm run build` + lint/typecheck green; no UI regression.

## Comments

### 2026-06-10T01:00:00Z — start
Per ADR 0003. Scoped to the shared foundation only; consumers (GYM-93 search `lang`, GYM-109 catalog,
GYM-94 dropdown) plug into it. Delegated to a frontend agent (background).

## Comments

### 2026-06-10 — done (c957b76)
Implemented on branch `i18n/gym-108-foundation`. Three files changed:
- `apps/web/src/i18n/locales.ts` — registry (`SUPPORTED_LOCALES`, `Locale`, `DEFAULT_LOCALE`).
- `apps/web/src/i18n/locale.ts` — `getLocale()` util + `useLocale()` hook.
- `apps/web/src/telegram/webapp.ts` — added `getTelegramLanguageCode()` minimal accessor.

`npm run build` (tsc strict + vite) passed green with zero new errors.
