# Tech Review — `apps/web` (код, библиотеки, переиспользование)

> Дата: 2026-06-11. Скоуп: `apps/web` (~9 000 строк, 65 файлов) + точки соприкосновения
> с `apps/api` и `packages/api-contract`. Статус: **approved 2026-06-12**; задачи —
> `tasks/tech-debt/` (GYM-124…GYM-129), i18n — существующий GYM-109.
> Не-цели: UI/UX (док 01), фичи прогрессии (док 03).

## 0. Общая оценка

Архитектура здоровая: contract-first типы из `@api-contract/schema`, единственная
HTTP-точка (`apiRequest`), TanStack Query с дисциплиной invalidation, токены вместо
магии почти везде, JSDoc на уровне, которого нет в большинстве прод-кодбейзов.
Главные долги: **i18n-каталог отсутствует**, **ноль тестов и линтера**, **дубли
компонентов/форм-логики**, несколько нарушений собственных правил (файлы >500 строк,
магические значения inline).

---

## 1. i18n — самый большой структурный долг (P0)

Факт: `i18n/locales.ts` + `locale.ts` (en/ru, GYM-108) существуют, но **каталога строк
нет** — все ~60+ UI-строк хардкоды в компонентах («Switch exercise», «No sets logged
yet.», «Couldn't save…», «Continue today», plural-логика `exercise/exercises` руками
в `DayCard` и т.д.).

Рекомендация (без новой библиотеки, в духе §1 спеки):
- `src/i18n/catalog.ts`: типизированный словарь `Record<MessageKey, {en: string; ru: string}>`
  + `t(key, params?)` с подстановками и **plural-правилами** (для ru их 3 формы —
  `exercise/exercises` через suffix не работает; нужна функция `plural(n, forms)`).
- `useT()` поверх `useLocale()`; единым PR-механическим проходом заменить строки.
- Date-форматирование: `formatDayHeading` / `ActivityGrid` WEEKDAYS / MONTHS — тоже
  локализовать (можно через `Intl.DateTimeFormat(locale)` вместо ручных массивов —
  бесплатная локализация + меньше кода).
- Если каталог перерастёт ~150 ключей — тогда рассматривать `i18next`; раньше — YAGNI.

## 2. Библиотеки: версии и кандидаты на обновление

Текущее (package.json) → состояние на июнь 2026:

| Пакет | Сейчас | Актуально | Вердикт |
|---|---|---|---|
| react / react-dom | ^18.2 | 19.x стабилен | Обновить осознанно: репо-гайд всё ещё «React 18», сначала поправить доку. Выгода: `useOptimistic` (подходит recap/optimistic-паттернам), ref-as-prop, лучшие ошибки гидрации (не используется SSR — выгода умеренная). Не срочно. |
| vite | ^5.0 | 6.x/7.x (свериться) | Обновить до последней мажорной (5→6→… безболезненно для такого конфига); быстрее dev/build, Node 20+. |
| tailwindcss | ^3.3 | 4.x | **Лучший ROI**: Tailwind 4 CSS-first конфиг (`@theme`) идеально ложится на токены в `tokens.css` — `tailwind.config.js` почти целиком исчезает, переменные объявляются один раз. Миграция средняя (контент-скан автоматический). |
| react-router-dom | ^6.20 | 7.x | Обновить заодно (v7 — переименование импортов, codemod есть). Бонус: встроенные view transitions для drill-in из дока 01. |
| @tanstack/react-query | ^5.59 | 5.x | Актуален. Ничего не делать. |
| echarts | ^5.5 | 6.x | Проверить changelog; не срочно. Важнее: **импортировать через `echarts/core` + только LineChart/Grid/Tooltip** — сейчас лениво грузится ВЕСЬ echarts (~1MB). Tree-shaking срежет чанк в ~3 раза. |
| echarts-for-react | ^3.0.2 | стагнирует | Обёртка тривиальная (init/setOption/resize) — при переходе на echarts/core проще заменить своим хуком ~40 строк и снять зависимость. |
| @twa-dev/sdk | ^8.0 | проверить | Bot API ушёл вперёд (9.x); сверить, не нужны ли новые события/методы. Не блокер. |

`apps/admin` (axios, lucide-react, clsx, tailwind-merge, React 18) — легаси-трек: не
обновлять, а планировать вывод из эксплуатации после полного переезда Mini App в
`apps/web` (зафиксировать в ROADMAP, чтобы не тащить две дизайн-системы).

## 3. Дубли и переиспользование (P1)

1. **`MuscleTile` ≡ `ExerciseTile`** и **`HiddenMuscleTile` ≡ `HiddenExerciseTile`**
   (RecordPicker.tsx) — побайтово одинаковые пары. Свести к `<PickerTile>` /
   `<PickerTile muted>`.
2. **Форма weight/reps продублирована трижды**: `SetLogger`, `SetEditor`, `AddSetInline`
   каждый держит `weightText/repsText + parseNumeric + valid`-логику. Вынести
   `useWeightRepsForm(initial?)` → `{weightProps, repsProps, values, valid, reset}`.
   Это же место, где живёт константа шага (см. §4).
3. **Recap-строка SetLogger vs `<SetRow>`** — одинаковая типографика `Set n — Xkg × Y`
   реализована дважды. Извлечь display-вариант `<SetFigure>` (без свайпа), SetRow
   композирует его.
4. **`BottomNav` measure-логика** — два почти одинаковых эффекта (useLayoutEffect +
   rAF-ремер). Объединить в один `useIndicatorPosition(activeIndex)`.
5. **Query keys рассыпаны строками** по useAnalytics/useRecord/useTraining (частично
   есть `daysKey`/`dayKey`/`logContextKey`). Завести `src/api/queryKeys.ts` — единая
   фабрика; инвалидация перестанет зависеть от ручного совпадения префиксов
   (сейчас `["analytics","summary"]` инвалидирует ключ с TZ-суффиксом только потому,
   что префикс совпал — работает, но хрупко и нигде не зафиксировано).

## 4. Хардкоды и нарушения собственных правил (P1)

- **`RecordPicker.tsx` = 1139 строк** — рушит правило «файл <500 строк» из CLAUDE.md.
  Естественный split: `useTilePressHandlers.ts` (хук), `PickerTile.tsx`,
  `ShowHiddenExpander.tsx`, `EmptyNewUser.tsx` → сам пикер ужмётся до ~400.
  `useRecord.ts` (547) и `ManageSheet.tsx` (539) — следующие кандидаты при касании.
- **Высота тайла 88px** повторена inline 8+ раз (`style={{height:"88px"}}`), при этом
  комментарий в index.css ссылается на `--tile-h`, которого **не существует**. Завести
  `--tile-h: 88px` в tokens.css + утилиту `.tile-h`.
- **`--stat-size` не определён** — `StatCard` читает `var(--stat-size, 2.5rem)`, токен
  нигде не объявлен (есть `text-stat` в tailwind). Убрать мёртвую переменную или
  объявить.
- Магические inline-значения: `fontSize: "0.625rem"` (ActivityGrid weekday rail),
  `maxWidth: "8rem"/"10rem"` (чип-капы в 4 местах — токенизировать `--chip-max`),
  `WEIGHT_STEP = 2.5` зашит в SetLogger + SetEditor + AddSetInline (константа в один
  модуль), z-index россыпью (`z-10/20/30/40` + проп) — мини-шкала
  `--z-{chrome,sheet,nested-sheet}`.
- `NavFab`: ветка-плейсхолдер с `console.debug` мертва (onRecord всегда передан) —
  убрать.

## 5. Корректность / надёжность (P1–P2)

- **Вложенные BottomSheet + BackButton**: оба открытых шита подписаны на
  `BackButton.onClick` одновременно — один Back, по-видимому, сработает в обоих
  (двойное закрытие / шаг пикера). Воспроизвести; фикс — стек хендлеров с одним
  активным верхним. (UX-эффект описан в доке 01 §1.4.)
- **`Container` cloneElement-хак** для stagger: клонирует только прямые valid-элементы;
  Fragment/массив/строка ломают индексацию, плюс molча перетирает className/style.
  CSS-only вариант: `main > div > * { animation: …; animation-delay: calc(…) }` через
  `:nth-child()` — снимет JS-хак целиком (и упростит фикс scroll-restoration из дока 01).
- **`ApiError` 401 не обрабатывается глобально**: протухший JWT (сессия в
  sessionStorage переживает перезапуск WebView) даст бесконечные ErrorState без
  re-auth. Добавить в `apiRequest` (или в QueryCache.onError) ветку 401 →
  `clearSessionToken()` + повторный `authenticateWithInitData()` один раз.
- **409 на `POST /training`** (коллизия номера сета, описана в спеке §12.8) в SetLogger
  не различается — generic message. Различить по `ApiError.status` и предложить
  «Set N already exists — refreshed your numbers» + invalidate log-context.
- `SetRow` свайп без `setPointerCapture` — палец, ушедший с элемента, теряет
  pointermove (ряд зависает полуоткрытым). Однострочный фикс
  `e.currentTarget.setPointerCapture(e.pointerId)`.
- `focus trap` в BottomSheet заявлен в JSDoc, не реализован (см. док 01 §5).

## 6. Тесты и тулинг (P0 по культуре, P1 по срочности)

- **Тестов нет вообще** (ни vitest, ни конфигурации). При этом чистой, идеально
  тестируемой логики много: `historyWindow` (окна/форматирование дат),
  `activityGridModel`, `parseNumeric`/Stepper bump, recap/nextSet/effectivePR derivation
  (SetLogger — там уже были реальные баги GYM-104/105!), exhaustion-логика History.
  Рекомендация: `vitest` + `@testing-library/react` точечно; первые ~30 unit-тестов
  закрывают самые регрессионно-опасные места без инфраструктурных затрат.
- **Линтера нет**: в `apps/web/package.json` нет ни eslint, ни prettier (у admin lint
  есть). Минимум: eslint flat config + `typescript-eslint` + `eslint-plugin-react-hooks`
  (в коде живут `eslint-disable-next-line react-hooks/exhaustive-deps` — а правило
  даже не подключено в этом пакете, т.е. disable-комментарии декоративные).
  Альтернатива одним инструментом — Biome (lint+format). Включить в CI перед build.
- `tsconfig` strict — уже хорошо; добавить `noUncheckedIndexedAccess` (поймает
  `muscleOptions[0]`-паттерны) — по готовности чинить выпавшее.
- CI: сейчас build-and-deploy; добавить шаг `tsc && lint && vitest run` до сборки
  образов.

## 7. Производительность (P2)

- ECharts: lazy-load уже есть (хорошо), но грузится полный бандл — см. §2
  (`echarts/core` + tree-shaking).
- `RecordSheet` маунтится в `AppShell` всегда (но рендерит null до open) — ок.
  `useTrainingDay(today)` в RecordSheet вызывается даже при закрытом шите —
  `enabled: open` сэкономит запрос на каждый заход в апку (день и так префетчится
  при открытии шита).
- Шрифты: preload корректный; проверить фактический вес ≤95KB бюджета (спека §9.2).
- `prefetchPickerReads` на каждый mount пикера — задумано; не трогать.

## 8. Приоритизированный план

| # | Что | Усилие | Риск |
|---|-----|--------|------|
| 1 | i18n-каталог + `t()` + plural ru/en, замена строк (§1) | M–L | низкий |
| 2 | eslint(+hooks)/vitest + CI-гейт (§6) | M | низкий |
| 3 | Фиксы корректности §5 (401, 409, pointer capture, back-стек) | M | низкий |
| 4 | Дедупликация §3 (PickerTile, useWeightRepsForm, SetFigure, queryKeys) | M | низкий |
| 5 | Токен-долг §4 (--tile-h, chip-max, z-шкала, split RecordPicker) | S–M | низкий |
| 6 | Tailwind 4 + Vite 7 (+router 7) апгрейд-пакет (§2) | M | средний |
| 7 | echarts/core tree-shaking, снять echarts-for-react (§7) | S–M | низкий |
| 8 | React 19 (после стабилизации остального) | M | средний |

Рекомендуемый порядок: 2 → 3 → 1 → 4/5 → 6/7 → 8. Линтер+тесты первыми — они
страхуют все остальные пункты.
