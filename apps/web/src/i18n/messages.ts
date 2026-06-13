/**
 * UI string catalog — GYM-109 (ADR 0003 Channel A). NO i18n library: a typed
 * dictionary keyed by `MessageKey`, exhaustively checked per locale by the
 * `Record<MessageKey, Record<Locale, string>>` shape.
 *
 * ADDING A LOCALE: extend SUPPORTED_LOCALES in locales.ts — the compiler then
 * forces a translation for EVERY key below (MESSAGES and PLURALS won't
 * typecheck until each entry carries the new locale). No other wiring needed.
 *
 * ADDING A KEY: add it to MESSAGES (or PLURALS for countable strings) — the
 * key union is derived from the object, so `t()` call sites stay typesafe.
 *
 * Conventions:
 *  - `{name}`-style placeholders, resolved by `t(key, params)` (catalog.ts).
 *  - Countable strings live in PLURALS as Intl.PluralRules form maps
 *    (en: one/other; ru: one/few/many + other for fractions).
 *  - The 8 fixed muscle labels are the `muscles.*` namespace; the API keeps
 *    returning canonical English names and `localizeMuscleName()` maps them
 *    at render time (unknown/custom names pass through unchanged).
 *  - "PR" stays Latin in both locales (brand mark).
 */
import type { Locale } from "@/i18n/locales";

/** One message in every supported locale (exhaustive by construction). */
type Translations = Record<Locale, string>;

export const MESSAGES = {
    // ── Common ──────────────────────────────────────────────────────────
    "common.cancel": { en: "Cancel", ru: "Отмена" },
    "common.back": { en: "Back", ru: "Назад" },
    "common.delete": { en: "Delete", ru: "Удалить" },
    "common.save": { en: "Save", ru: "Сохранить" },
    "common.add": { en: "Add", ru: "Добавить" },
    "common.done": { en: "Done", ru: "Готово" },
    "common.loading": { en: "Loading…", ru: "Загрузка…" },
    "common.close": { en: "Close", ru: "Закрыть" },
    "common.dismiss": { en: "Dismiss", ru: "Скрыть" },
    "common.retry": { en: "Try again", ru: "Повторить" },

    // ── Errors / auth ───────────────────────────────────────────────────
    "error.generic": { en: "Something went wrong.", ru: "Что-то пошло не так." },
    "auth.errorFallback": {
        en: "Could not sign you in via Telegram.",
        ru: "Не удалось войти через Telegram.",
    },
    "auth.failed": { en: "Authentication failed", ru: "Не удалось авторизоваться" },

    // ── Navigation / shell ──────────────────────────────────────────────
    "nav.dashboard": { en: "Dashboard", ru: "Обзор" },
    "nav.progress": { en: "Progress", ru: "Прогресс" },
    "nav.history": { en: "History", ru: "История" },
    "nav.profile": { en: "Profile", ru: "Профиль" },
    "nav.appTitle": { en: "Gym", ru: "Gym" },
    "nav.recordTraining": { en: "Record training", ru: "Записать тренировку" },

    // ── Profile (stub) ──────────────────────────────────────────────────
    "profile.title": { en: "PROFILE", ru: "ПРОФИЛЬ" },
    "profile.comingSoon": { en: "Coming soon", ru: "Скоро будет" },

    // ── Empty states ────────────────────────────────────────────────────
    "empty.noTrainingsTitle": { en: "No trainings yet", ru: "Тренировок пока нет" },
    "empty.noTrainingsSubtitle": {
        en: "Tap + to log your first set.",
        ru: "Нажмите «+», чтобы записать первый сет.",
    },
    "empty.logASet": { en: "Log a set", ru: "Записать сет" },
    "empty.noDataTitle": { en: "No data yet", ru: "Пока нет данных" },
    "empty.noDataSubtitle": {
        en: "No logged sets for {exercise}. Tap + to record one.",
        ru: "Нет записанных сетов для «{exercise}». Нажмите «+», чтобы добавить.",
    },
    "empty.dayTitle": { en: "Empty day", ru: "Пустой день" },
    "empty.dayNotFound": {
        en: "This day has no trainings.",
        ru: "В этот день тренировок не было.",
    },
    "empty.dayNoSets": {
        en: "No sets recorded on this day.",
        ru: "В этот день нет записанных сетов.",
    },

    // ── History list / day detail ───────────────────────────────────────
    "history.loadEarlier": { en: "Load earlier", ru: "Показать раньше" },
    "history.beginning": { en: "That's the beginning.", ru: "Это самое начало." },
    "history.saveRestored": {
        en: "Couldn't save — restored.",
        ru: "Не удалось сохранить — вернули как было.",
    },
    "history.deleteRestored": {
        en: "Couldn't delete — restored.",
        ru: "Не удалось удалить — вернули как было.",
    },

    // ── Activity grid (Dashboard) ───────────────────────────────────────
    "activity.title": { en: "Activity", ru: "Активность" },
    "activity.window": { en: "Last 26 weeks", ru: "Последние 26 недель" },
    "activity.less": { en: "Less", ru: "Меньше" },
    "activity.more": { en: "More", ru: "Больше" },
    "activity.tapADay": {
        en: "Tap a day to inspect",
        ru: "Нажмите на день, чтобы посмотреть",
    },
    "activity.cellTooltip": { en: "{sets} on {date}", ru: "{sets} — {date}" },

    // ── Summary cards (Dashboard) ───────────────────────────────────────
    "summary.exercises": { en: "Exercises", ru: "Упражнения" },
    "summary.sets": { en: "Sets", ru: "Сеты" },
    "summary.prs": { en: "PRs set", ru: "Рекорды" },
    "summary.weekStreak": { en: "Week streak", ru: "Недель подряд" },
    "pr": { en: "PR", ru: "PR" },
    // GYM-153: kind-specific PR labels for the SetRow middle marker.
    // Short fallback "PR" is the existing `pr` key (reused on narrow rows
    // and for the DayCard day-level badge which has no kind).
    "pr.weight": { en: "Weight PR", ru: "Weight PR" },
    "pr.reps": { en: "Reps PR", ru: "Reps PR" },

    // ── THIS WEEK card (Dashboard, GYM-136) — ▲/▼ are unicode geometric
    // figures (the GYM-130 delta language), not emojis. Sets reuse the
    // existing count.sets plural ("сеты", not "подходы").
    "weekCompare.title": { en: "THIS WEEK", ru: "НА ЭТОЙ НЕДЕЛЕ" },
    "weekCompare.volume": { en: "{volume} kg", ru: "{volume} кг" },
    "weekDelta.upVolume": { en: "▲ +{amount} kg", ru: "▲ +{amount} кг" },
    "weekDelta.downVolume": { en: "▼ −{amount} kg", ru: "▼ −{amount} кг" },
    "weekCompare.vsLastAria": {
        en: "Compared to last week",
        ru: "По сравнению с прошлой неделей",
    },

    // ── Progress page / chart ───────────────────────────────────────────
    "progress.viewAria": { en: "Progress view", ru: "Вид графика" },
    "progress.byWeight": { en: "By Weight", ru: "По весу" },
    "progress.bySet": { en: "By Set", ru: "По сетам" },
    // GYM-133: "e1RM" stays Latin in both locales (a formula name, like "PR").
    "progress.e1rm": { en: "e1RM", ru: "e1RM" },
    "chart.maxWeight": { en: "Max weight", ru: "Макс. вес" },
    "chart.e1rm": { en: "e1RM", ru: "e1RM" },

    // ── Shared field labels / figures ───────────────────────────────────
    "label.muscle": { en: "Muscle", ru: "Мышца" },
    "label.exercise": { en: "Exercise", ru: "Упражнение" },
    "label.weight": { en: "Weight", ru: "Вес" },
    "label.reps": { en: "Reps", ru: "Повторы" },
    "unit.kg": { en: "kg", ru: "кг" },
    "figure.weightReps": { en: "{weight}kg × {reps}", ru: "{weight}кг × {reps}" },
    "set.n": { en: "Set {n}", ru: "Сет {n}" },

    // ── Record picker (Phase A) ─────────────────────────────────────────
    "record.title": { en: "RECORD", ru: "ЗАПИСЬ" },
    "record.continueToday": { en: "Continue today", ru: "Продолжить сегодня" },
    "picker.muscles": { en: "Muscles", ru: "Мышцы" },
    "picker.addMuscle": { en: "+ Muscle", ru: "+ Мышца" },
    "picker.addExercise": { en: "+ Exercise", ru: "+ Упражнение" },
    "picker.showAll": { en: "Show all ({n})", ru: "Показать все ({n})" },
    "picker.showHiddenMuscles": {
        en: "Show hidden muscles",
        ru: "Показать скрытые мышцы",
    },
    "picker.showHiddenExercises": {
        en: "Show hidden exercises",
        ru: "Показать скрытые упражнения",
    },
    "picker.unhide": { en: "Unhide", ru: "Вернуть" },
    "picker.unhiding": { en: "Unhiding…", ru: "Возвращаем…" },
    "picker.loadMusclesError": {
        en: "Couldn't load muscles.",
        ru: "Не удалось загрузить мышцы.",
    },
    "picker.loadExercisesError": {
        en: "Couldn't load exercises.",
        ru: "Не удалось загрузить упражнения.",
    },
    "picker.addError": {
        en: "Couldn't add that — try again.",
        ru: "Не удалось добавить — попробуйте ещё раз.",
    },
    "picker.alreadyHave": {
        en: 'You already have "{name}".',
        ru: "У вас уже есть «{name}».",
    },
    "picker.newMusclePlaceholder": { en: "New muscle name", ru: "Название мышцы" },

    // ── Empty-new-user prompt ───────────────────────────────────────────
    "emptyUser.title": {
        en: "ADD YOUR FIRST EXERCISE",
        ru: "ДОБАВЬТЕ ПЕРВОЕ УПРАЖНЕНИЕ",
    },
    "emptyUser.subtitle": {
        en: "Name a muscle, then an exercise under it — you'll log your first set right after.",
        ru: "Назовите мышцу, затем упражнение — и сразу запишете первый сет.",
    },
    "emptyUser.musclePlaceholder": {
        en: "Muscle (e.g. Chest)",
        ru: "Мышца (например, Грудь)",
    },
    "emptyUser.exercisePlaceholder": {
        en: "Exercise in {muscle}",
        ru: "Упражнение — {muscle}",
    },

    // ── Exercise search field ───────────────────────────────────────────
    "search.placeholder": { en: "Search in {muscle}…", ru: "Поиск в {muscle}…" },
    "search.cancelAria": { en: "Cancel search", ru: "Отменить поиск" },
    "search.suggestionsAria": {
        en: "Exercise suggestions for {muscle}",
        ru: "Варианты упражнений для {muscle}",
    },
    "search.unavailable": { en: "Search unavailable.", ru: "Поиск недоступен." },
    "search.retry": { en: "Retry", ru: "Повторить" },
    "search.noMatches": {
        en: "No matches — create it below.",
        ru: "Ничего не найдено — создайте ниже.",
    },
    "search.create": { en: "Create", ru: "Создать" },

    // ── Set logger (Phase B) ────────────────────────────────────────────
    "logger.switchExercise": { en: "Switch exercise", ru: "Сменить упражнение" },
    "logger.today": { en: "Today", ru: "Сегодня" },
    "logger.noSetsYet": { en: "No sets logged yet.", ru: "Сетов пока нет." },
    "logger.setHeading": { en: "SET {n}", ru: "СЕТ {n}" },
    "logger.prValue": { en: "PR {weight}kg", ru: "PR {weight}кг" },
    "logger.loadingNumbers": {
        en: "loading your numbers…",
        ru: "загружаем ваши цифры…",
    },
    "logger.saveSet": { en: "Save set {n}", ru: "Записать сет {n}" },
    // GYM-131: Save-button success morph (compact, one line, no layout shift).
    "logger.savedSet": {
        en: "Saved set {n} — {weight}×{reps}",
        ru: "Записан сет {n} — {weight}×{reps}",
    },
    // GYM-131 #5: in-sheet PR banner (Bebas via font-display; restrained).
    "logger.prBanner": { en: "NEW PR · {weight}KG", ru: "НОВЫЙ PR · {weight}КГ" },
    // GYM-135 trend chip — ▲/▼/→ are unicode geometric figures, not emojis.
    "trend.up": { en: "▲ {weeks}w", ru: "▲ {weeks} нед" },
    "trend.down": { en: "▼ {weeks}w", ru: "▼ {weeks} нед" },
    "trend.flat": { en: "→ {weeks}w", ru: "→ {weeks} нед" },
    // Screen-reader alternative for the aria-hidden sparkline + chip group.
    "trend.upAria": {
        en: "Estimated 1RM trending up over the last {weeks} weeks",
        ru: "Расчётный 1ПМ растёт за последние {weeks} недель",
    },
    "trend.downAria": {
        en: "Estimated 1RM trending down over the last {weeks} weeks",
        ru: "Расчётный 1ПМ снижается за последние {weeks} недель",
    },
    "trend.flatAria": {
        en: "Estimated 1RM flat over the last {weeks} weeks",
        ru: "Расчётный 1ПМ без изменений за последние {weeks} недель",
    },
    "save.error409": {
        en: "Set {n} already exists — refreshed your numbers.",
        ru: "Сет {n} уже записан — мы обновили номера.",
    },
    "save.errorGeneric": {
        en: "Couldn't save that set — try again.",
        ru: "Не удалось сохранить сет — попробуйте ещё раз.",
    },

    // ── Ghost recap comparison (GYM-130) ────────────────────────────────
    // ▲/▼ are unicode geometric figures (like the "— · —" placeholder),
    // not emojis; rendered uppercase via CSS where needed.
    "recap.today": { en: "Today", ru: "Сегодня" },
    "recap.lastTime": { en: "Last time", ru: "Прошлый раз" },
    "delta.upWeight": { en: "▲ +{amount}kg", ru: "▲ +{amount}кг" },
    "delta.downWeight": { en: "▼ −{amount}kg", ru: "▼ −{amount}кг" },

    // ── Session summary on Done (GYM-132) — restrained, no exclamations ──
    "sessionSummary.title": { en: "DONE", ru: "ГОТОВО" },
    "sessionSummary.volume": { en: "{volume} kg volume", ru: "{volume} кг объём" },
    // "PR" stays Latin in both locales (brand mark); count via {n}.
    "sessionSummary.prCount": { en: "{n} PR", ru: "{n} PR" },
    "sessionSummary.weekStreak": {
        en: "Week streak: {n}",
        ru: "Недель подряд: {n}",
    },
    "sessionSummary.tapToClose": {
        en: "Tap to close",
        ru: "Нажмите, чтобы закрыть",
    },

    // ── Stepper (aria) ──────────────────────────────────────────────────
    "stepper.decrease": { en: "decrease", ru: "уменьшить" },
    "stepper.increase": { en: "increase", ru: "увеличить" },

    // ── Set editor / set rows ───────────────────────────────────────────
    "editor.move": { en: "Move", ru: "Перенести" },
    "editor.moveSetAria": {
        en: "Move {exercise} set {n}",
        ru: "Перенести {exercise}, сет {n}",
    },
    "editor.deleteSetAria": {
        en: "Delete {exercise} set {n}",
        ru: "Удалить {exercise}, сет {n}",
    },
    "editor.deleteThisSet": { en: "Delete this set?", ru: "Удалить этот сет?" },
    "setRow.deleteAria": { en: "Delete set {n}", ru: "Удалить сет {n}" },

    // ── Add-set inline (History day) ────────────────────────────────────
    "addSet.trigger": { en: "Add set", ru: "Добавить сет" },
    "addSet.triggerAria": {
        en: "Add set to {exercise}",
        ru: "Добавить сет: {exercise}",
    },
    "addSet.adding": { en: "Adding…", ru: "Добавляем…" },
    "addSet.exists": {
        en: "That set already exists — the set number may have changed.",
        ru: "Такой сет уже есть — номер сета мог измениться.",
    },
    "addSet.error": {
        en: "Couldn't add the set — try again.",
        ru: "Не удалось добавить сет — попробуйте ещё раз.",
    },

    // ── Move-set panel ──────────────────────────────────────────────────
    "move.title": { en: "Move to", ru: "Перенести" },
    "move.day": { en: "Day", ru: "День" },
    "move.exerciseChange": { en: "{exercise} — change", ru: "{exercise} — изменить" },
    "move.clearExercise": {
        en: "Clear exercise change",
        ru: "Сбросить смену упражнения",
    },
    "move.targetMuscle": { en: "Target muscle", ru: "Куда: мышца" },
    "move.targetExercise": { en: "Target exercise", ru: "Куда: упражнение" },
    "move.moving": { en: "Moving…", ru: "Переносим…" },
    "move.moveSet": { en: "Move set", ru: "Перенести сет" },
    "move.slotTaken": {
        en: "That slot is already taken — pick a different day or exercise.",
        ru: "Это место уже занято — выберите другой день или упражнение.",
    },
    "move.checkSelection": {
        en: "Couldn't move — check your selection.",
        ru: "Не удалось перенести — проверьте выбор.",
    },
    "move.error": {
        en: "Couldn't move — try again.",
        ru: "Не удалось перенести — попробуйте ещё раз.",
    },

    // ── Manage sheet ────────────────────────────────────────────────────
    "manage.rename": { en: "Rename", ru: "Переименовать" },
    "manage.moveToAnotherMuscle": {
        en: "Move to another muscle",
        ru: "Перенести в другую мышцу",
    },
    "manage.hide": { en: "Hide from my list", ru: "Скрыть из моего списка" },
    "manage.hideAction": { en: "Hide", ru: "Скрыть" },
    "manage.hiding": { en: "Hiding…", ru: "Скрываем…" },
    "manage.deleting": { en: "Deleting…", ru: "Удаляем…" },
    "manage.nameInUse": {
        en: "That name is already in use.",
        ru: "Это название уже занято.",
    },
    "manage.renameError": {
        en: "Couldn't rename — try again.",
        ru: "Не удалось переименовать — попробуйте ещё раз.",
    },
    "manage.deleteError": {
        en: "Couldn't delete — try again.",
        ru: "Не удалось удалить — попробуйте ещё раз.",
    },
    "manage.deleteConfirm": {
        en: 'Delete "{name}"? This cannot be undone.',
        ru: "Удалить «{name}»? Это нельзя отменить.",
    },
    "manage.hasHistory": {
        en: '"{name}" has logged history and can\'t be deleted. Hide it from your picker instead?',
        ru: "У «{name}» есть записанная история — удалить нельзя. Скрыть из списка?",
    },
    "manage.moveCollision": {
        en: "You already have an exercise with this name in {muscle}.",
        ru: "В «{muscle}» уже есть упражнение с таким названием.",
    },
    "manage.cantMove": {
        en: "This exercise can't be moved.",
        ru: "Это упражнение нельзя перенести.",
    },
    "manage.targetNotFound": {
        en: "Target muscle not found — try again.",
        ru: "Целевая мышца не найдена — попробуйте ещё раз.",
    },
    "manage.noOtherMuscles": {
        en: "No other muscles available.",
        ru: "Других мышц нет.",
    },
    "manage.newMuscleName": { en: "New muscle name", ru: "Новое название мышцы" },
    "manage.newExerciseName": {
        en: "New exercise name",
        ru: "Новое название упражнения",
    },

    // ── The 8 fixed muscle labels (ADR 0003: frontend catalog, no DB table) ──
    "muscles.abs": { en: "ABS", ru: "Пресс" },
    "muscles.back": { en: "Back", ru: "Спина" },
    "muscles.biceps": { en: "Biceps", ru: "Бицепс" },
    "muscles.chest": { en: "Chest", ru: "Грудь" },
    "muscles.forearms": { en: "Forearms", ru: "Предплечья" },
    "muscles.legs": { en: "Legs", ru: "Ноги" },
    "muscles.shoulders": { en: "Shoulders", ru: "Плечи" },
    "muscles.triceps": { en: "Triceps", ru: "Трицепс" },
} as const satisfies Record<string, Translations>;

/** Every translatable message key (derived — never drifts from the data). */
export type MessageKey = keyof typeof MESSAGES;

/**
 * Plural form map per Intl.PluralRules category. `other` is mandatory (the
 * universal fallback — also covers ru fractions like "1,5 сета"); the rest
 * are per-language: en uses one/other, ru uses one/few/many.
 */
export interface PluralForms {
    one?: string;
    few?: string;
    many?: string;
    other: string;
}

export const PLURALS = {
    "count.exercises": {
        en: { one: "{n} exercise", other: "{n} exercises" },
        ru: {
            one: "{n} упражнение",
            few: "{n} упражнения",
            many: "{n} упражнений",
            other: "{n} упражнения",
        },
    },
    "count.sets": {
        en: { one: "{n} set", other: "{n} sets" },
        ru: {
            one: "{n} сет",
            few: "{n} сета",
            many: "{n} сетов",
            other: "{n} сета",
        },
    },
    // GYM-130: reps-tiebreak deltas (weights equal). ru uses the invariant
    // abbreviation "повт." across all plural categories.
    "delta.upReps": {
        en: { one: "▲ +{n} rep", other: "▲ +{n} reps" },
        ru: { other: "▲ +{n} повт." },
    },
    "delta.downReps": {
        en: { one: "▼ −{n} rep", other: "▼ −{n} reps" },
        ru: { other: "▼ −{n} повт." },
    },
    // GYM-136: THIS WEEK card set-count deltas vs last week (▲/▼ are the
    // same unicode geometric figures as the GYM-130 recap deltas).
    "weekDelta.upSets": {
        en: { one: "▲ +{n} set", other: "▲ +{n} sets" },
        ru: {
            one: "▲ +{n} сет",
            few: "▲ +{n} сета",
            many: "▲ +{n} сетов",
            other: "▲ +{n} сета",
        },
    },
    "weekDelta.downSets": {
        en: { one: "▼ −{n} set", other: "▼ −{n} sets" },
        ru: {
            one: "▼ −{n} сет",
            few: "▼ −{n} сета",
            many: "▼ −{n} сетов",
            other: "▼ −{n} сета",
        },
    },
    // GYM-132: session-summary "beat last session" line (▲ is the same
    // unicode geometric figure as the recap deltas, not an emoji).
    "sessionSummary.beatLast": {
        en: {
            one: "▲ {n} set beat last session",
            other: "▲ {n} sets beat last session",
        },
        ru: {
            one: "▲ {n} сет лучше прошлого раза",
            few: "▲ {n} сета лучше прошлого раза",
            many: "▲ {n} сетов лучше прошлого раза",
            other: "▲ {n} сета лучше прошлого раза",
        },
    },
} as const satisfies Record<string, Record<Locale, PluralForms>>;

/** Every countable message key (derived from the plural catalog). */
export type PluralKey = keyof typeof PLURALS;
