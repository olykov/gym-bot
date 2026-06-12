---
schema_version: 1
id: GYM-109
title: "ui-i18n: frontend string catalog (en/ru) + extract hardcoded strings + 8 muscle labels"
slug: gym-109-ui-string-catalog
status: review
priority: medium
type: feature
labels: [i18n, frontend, design, ux]
assignee: null
model: null
reporter: oleksii
created: 2026-06-10T01:00:00Z
start_date: 2026-06-12T16:00:00Z
finish_date: null
updated: 2026-06-12T16:45:00Z
epic: ui-i18n
depends_on: [GYM-108]
blocks: []
related: []
commits: []
tests: []
design_reports: ["docs/adr/0003-i18n-architecture.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-109 — ui-i18n: UI string catalog (Channel A)

## Problem
Channel A of [ADR 0003](../../docs/adr/0003-i18n-architecture.md): UI chrome (buttons, headings, toasts)
and the 8 fixed muscle names are hardcoded English. They must localize by the resolved locale (GYM-108).
Muscles localize HERE (frontend catalog), NOT via a DB `muscle_alias` table.

## Solution
1. Add a lightweight i18n lib + per-locale catalogs (`en.json`/`ru.json`) keyed by the GYM-108 registry.
2. Extract hardcoded strings from `apps/web` components into keys; render via the catalog + `getLocale()`.
3. Include the 8 muscle labels as a `muscles.*` namespace (API still returns canonical id/name; frontend
   maps to the localized label).
4. Must go through the `frontend-design-engineer` agent + `frontend-design` plugin (UI work per CLAUDE.md).

## Acceptance criteria
- [x] Switching Telegram language to `ru` localizes chrome + muscle labels; `en`/unknown stays English.
      (Implemented + unit-tested via explicit-locale paths; on-device ru switch check by the operator
      is still pending.)
- [x] No string left hardcoded in touched components; build + typecheck green.

## Comments

### 2026-06-10T01:00:00Z — created
Self-contained frontend wave; scheduled after the foundation + exercise-search land. Does not block
GYM-93/94.

### 2026-06-12T10:10:00Z — tech-review input (docs/review/02-tech-review.md §1)
The 2026-06 frontend review flags this as the biggest structural debt (~60+ hardcoded strings) and
adds implementation notes to weigh at impl time:
- Consider NO new library (spec §1): a typed `catalog.ts` (`Record<MessageKey,{en,ru}>`) + `t()` +
  `useT()` over `useLocale()`. Revisit i18next only if the catalog outgrows ~150 keys.
- Russian needs real plural rules (3 forms) — the `exercise/exercises` suffix pattern in DayCard
  won't translate; provide `plural(n, forms)`.
- Dates too: `formatDayHeading` + ActivityGrid WEEKDAYS/MONTHS — prefer `Intl.DateTimeFormat(locale)`
  over hand-rolled arrays (free localization, less code).
- New strings from GYM-118 (empty-state CTAs) and the progression epic (GYM-130…132) should land as
  keys if this task is done first — coordinate ordering.

### 2026-06-12T16:45:00Z — implemented (agent wave 5b)
Implemented per the tech-review note: **NO i18n library** — a typed catalog. Approach:
- `src/i18n/messages.ts` (data): `MESSAGES as const satisfies Record<string, Record<Locale, string>>`
  → derived `MessageKey` union, **138 message keys** + `PLURALS` (**2 countable keys**:
  `count.exercises`, `count.sets`) with en one/other and ru one/few/many(+other for fractions) forms.
  Adding a locale = extend `SUPPORTED_LOCALES`; the types force every entry to carry it.
- `src/i18n/catalog.ts`: `translate/t(key, params?)` with `{name}` interpolation,
  `plural(n, forms, locale)` via cached `Intl.PluralRules`, `translatePlural/tPlural`,
  `localizeMuscleName()` (the 8 fixed muscles → `muscles.*` namespace; unknown/custom names pass
  through), and `useT()` → `{ t, tp, muscle, locale }` over `useLocale()`.
- `src/i18n/datetime.ts`: Intl-based short weekday/month helpers replacing the hand-rolled
  WEEKDAYS/MONTHS arrays in `historyWindow.formatDayHeading` (`MON 08 JUN` / `ПН 08 ИЮН`, year rule
  kept), `activityGridModel.monthLabels` + new `weekdayRail()`, and `echartsTheme.formatAxisDate`.
  Pure fns take an optional `locale` param defaulting to `getLocale()` — tests pass `"en"`/`"ru"`.
- `i18n/locale.ts` now reads `window.Telegram.WebApp…language_code` directly (not via
  `@/telegram/webapp`) so pure modules never pull @twa-dev/sdk into Node/vitest (same value at runtime).
- Extracted every hardcoded UI string (pages, shell/nav labels via `navConfig.labelKey`, record flow,
  SetLogger, SetEditor/ManageSheet/MoveSetPanel/AddSetInline, DayCard plurals, Empty/Error states,
  AuthGate/AuthProvider, BottomSheet/Stepper/SetRow aria-labels, ActivityGrid, SummaryCards,
  SegmentedControl options, chart series/tooltip incl. kg→кг). Muscle labels localized at all display
  sites (tiles, chips, ChipRow via new `display` field, panels, move/manage views) while API names stay
  canonical query keys. Server 422 detail intentionally passes through untranslated.
- Terminology (bot has no ru strings to match — checked): Set→Сет, Reps→Повторы, Weight→Вес,
  PR→PR (latin), Done→Готово, Save set N→Записать сет N, Switch exercise→Сменить упражнение,
  Continue today→Продолжить сегодня; muscles: Пресс/Спина/Бицепс/Грудь/Предплечья/Ноги/Плечи/Трицепс.
- Files: 4 new (`messages.ts`, `catalog.ts`, `datetime.ts`, `catalog.test.ts`), 43 modified
  (40 source + 3 updated test files).
- Verification: bench `tsc --noEmit` + `eslint --max-warnings 0` + `vitest run` (**112 passed**, was 93;
  date tests updated to explicit locale + new ru cases, catalog tests cover interpolation, ru
  one/few/many, muscle pass-through) + `vite build` — all green. Grep: no user-visible English literal
  left in JSX outside the catalog (comments stay English).
- Pending: on-device ru-switch smoke check by the operator (ru copy review welcome).
- Suggested commit: `Add typed en/ru UI string catalog with plurals`
