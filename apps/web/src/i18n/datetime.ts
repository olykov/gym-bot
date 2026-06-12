/**
 * Locale-aware short date parts — GYM-109. Replaces the hand-rolled
 * WEEKDAYS / MONTHS arrays (historyWindow, activityGridModel, echartsTheme)
 * with Intl.DateTimeFormat so every supported locale formats for free.
 *
 * Two month flavours exist on purpose:
 *  - `shortMonthInDate` — the month as written NEXT TO a day number
 *    (en "Jun", ru genitive "июн"); used by `DD MON` compositions.
 *  - `shortMonthStandalone` — the month label on its own
 *    (en "Jan", ru "Янв"); used by the activity-grid month row.
 * Russian Intl output carries an abbreviation dot ("июн.") — stripped here
 * so compositions stay condensed; en output is unchanged.
 */
import type { Locale } from "@/i18n/locales";

// One formatter per (kind, locale) — Intl.DateTimeFormat creation is costly.
const weekdayFmts = new Map<Locale, Intl.DateTimeFormat>();
const dayMonthFmts = new Map<Locale, Intl.DateTimeFormat>();
const monthFmts = new Map<Locale, Intl.DateTimeFormat>();

function cached(
    cache: Map<Locale, Intl.DateTimeFormat>,
    locale: Locale,
    options: Intl.DateTimeFormatOptions,
): Intl.DateTimeFormat {
    let fmt = cache.get(locale);
    if (!fmt) {
        fmt = new Intl.DateTimeFormat(locale, options);
        cache.set(locale, fmt);
    }
    return fmt;
}

/** Strip the trailing abbreviation dot Intl adds in some locales ("июн."). */
function stripDot(value: string): string {
    return value.endsWith(".") ? value.slice(0, -1) : value;
}

/** Short weekday as Intl emits it (en "Mon", ru "пн"). */
export function shortWeekday(date: Date, locale: Locale): string {
    return stripDot(cached(weekdayFmts, locale, { weekday: "short" }).format(date));
}

/** Short month as written next to a day number (en "Jun", ru "июн"). */
export function shortMonthInDate(date: Date, locale: Locale): string {
    const parts = cached(dayMonthFmts, locale, {
        day: "2-digit",
        month: "short",
    }).formatToParts(date);
    const month = parts.find((p) => p.type === "month")?.value ?? "";
    return stripDot(month);
}

/** Standalone short month label, first letter capitalized (en "Jan", ru "Янв"). */
export function shortMonthStandalone(monthIndex: number, locale: Locale): string {
    const raw = stripDot(
        cached(monthFmts, locale, { month: "short" }).format(
            new Date(2024, monthIndex, 1),
        ),
    );
    return raw.charAt(0).toLocaleUpperCase(locale) + raw.slice(1);
}
