# Handoff — ветка `fable-tasks` (2026-06-12)

23 задачи (GYM-109, GYM-116…GYM-137) реализованы агентскими волнами и стоят в `status: review`.
Коммитов нет (договорённость: коммитишь сам). Этот док — что сделать руками, в каком порядке.

## 0. СНАЧАЛА: почистить git (обязательно, иначе git не работает)

В песочнице остались висячие lock-файлы и один случайный тестовый коммит. На своей машине:

```bash
cd ~/oleksii/tg-app-gym-bot
rm -f .git/HEAD.lock .git/index.lock .git/objects/maintenance.lock .git/objects/*/tmp_obj_*
git log --oneline -1          # увидишь "test commit (will reset)"
git reset --soft HEAD~1       # снять тестовый коммит (содержимое остаётся staged)
git restore --staged .        # разстейджить всё
git status                    # всё должно быть в untracked/modified, ничего не потеряно
```

## 1. Верификация (что уже проверено / что осталось тебе)

Проверено в песочнице на финальном состоянии: `tsc --noEmit`, `eslint --max-warnings 0`,
**vitest 185/185**, `vite build` (бандл: main 450KB / chart 516KB — был 1056KB, JS gzip суммарно −36%),
py_compile всех python-файлов, openapi 3.1 валиден, оба клиента перегенерированы.

Осталось тебе (отмечено и в задачах):
- `apps/api` интеграционные тесты НАПИСАНЫ, но НЕ ЗАПУСКАЛИСЬ (нужен живой Postgres):
  прогнать suite (test_gym134_exercise_trend.py, test_gym136_week_compare.py + весь регресс).
- Бот: ручной smoke дельты (шаги в GYM-137).
- Device-smoke Mini App (телефон, обе темы, 360px): запись сета (ghost recap, хореография,
  PR-баннер, summary по Done), drag-to-dismiss шита, hold-to-repeat степпера, скролл/переходы
  History, тач по Activity-гриду, переключение языка на ru, e1RM-режим графика, спарклайн.
- Опционально: `git rm tailwind.config.js postcss.config.js` (после TW4 это no-op заглушки,
  из песочницы удалить было нельзя).

## 2. План коммитов

Per-task нарезка уже нечестна — одни и те же файлы (SetLogger, tokens.css, queryKeys…)
трогались в 6+ волнах. Рекомендую **5 тематических коммитов** финального состояния:

```bash
# 1. Доки + задачи (kanban)
git add docs/review/ tasks/
git commit -m "Add frontend review docs and GYM-116..137 backlog with implementation notes"

# 2. Контракт + API
git add packages/api-contract/openapi.yaml packages/api-contract/clients/ apps/api/
git commit -m "Add exercise-trend and week-compare endpoints, has_pr flag"

# 3. Бот
git add apps/bot/modules/delta.py apps/bot/modules/confirmation.py apps/bot/modules/handlers.py
git commit -m "Show last-session delta in bot save confirmation"

# 4. Весь apps/web (UX-фиксы, motion, рефакторинг, i18n, progression, апгрейды)
git add apps/web/ docs/frontend-spec.md
git commit -m "Web: UX fixes, i18n, progression features, tooling and upgrades"

# 5. CI
git add .github/workflows/ci.yaml
git commit -m "Gate deploy on web typecheck, lint and tests"
```

Если хочешь гранулярнее — в каждом task-файле есть suggested commit message и список файлов;
но учитывай пересечения (отмечены в комментариях задач «overlap»).

После коммитов: проставить SHA в `commits:` соответствующих задач + `status: done`,
`finish_date` — и `validate_tasks.py` перед пушем. Деплой уйдёт только после merge в main
(CI теперь дополнительно гонит web-checks до сборки образов).

## 3. Сводка реализованного (по волнам)

| Волна | Задачи | Суть |
|---|---|---|
| 1 | GYM-124 | eslint + vitest с нуля (48 тестов), CI-гейт web-checks |
| 2 | GYM-125, 119 | 401 self-heal, 409-сообщение, pointer capture, focus trap; BackButton-стек для вложенных шитов |
| 3 | GYM-116, 121, 117, 118 | scroll restoration + reveal только вперёд; направленные view-transitions; тач-инспекция Activity-грида; empty-states → CTA на `+` |
| 4 | GYM-120, 122, 123 | drag-to-dismiss шита; hold-to-repeat степпера; polish-batch (месяцы на гриде, `— · —`, SVG вместо ❌, a11y, контраст-аудит) |
| 5 | GYM-126, 127, 109 | дедуп (PickerTile, useWeightRepsForm, SetFigure, queryKeys); токены + split RecordPicker 1139→467; **i18n en/ru, 138 ключей + плюрализация + Intl-даты** |
| 6 | GYM-130, 131, 132 | **ghost recap TODAY/LAST TIME + дельты (вес→повторы, ASC)**; хореография Save (морф кнопки, ролл цифры, PR-баннер); session summary по Done (1 тап, ноль сети) |
| 7 | GYM-133, 134, 137, 135, 136 | e1RM-режим + типы PR; exercise-trend API; дельта в боте; спарклайн в SetLogger; week-compare + PR-маркеры дней |
| 8 | GYM-128, 129 | Vite 8, react-router 7, **Tailwind 4 CSS-first**; echarts tree-shaking (чанк −51%) |

Отложено по твоим решениям: overload-streak (№4), React 19 (вне скоупа GYM-128).
