/**
 * Pure date model for the History day-list window-based pagination (spec §11.2)
 * — no React, no DOM. Mirrors the activity grid's window discipline: the list
 * paginates by an expanding `from`/`to` window, never by offset/limit.
 *
 * v1 default window = the last ~12 weeks (84 days). "Load earlier" expands the
 * window backward another step (same `to`, `from -= STEP_DAYS`) so a multi-year
 * history never loads as one unbounded list (the §0/ARCH §2 anti-pattern).
 */
import type { Locale } from "@/i18n/locales";
import { getLocale } from "@/i18n/locale";
import { shortMonthInDate, shortWeekday } from "@/i18n/datetime";

/** One pagination step = ~12 weeks (matches the spec's default + expand size). */
export const STEP_DAYS = 84;

export interface DateWindow {
    from: string;
    to: string;
}

/** Local YYYY-MM-DD (avoids the UTC off-by-one from toISOString). */
export function toISODate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

/**
 * The window for a given number of steps back from today.
 *
 * @param steps - how many STEP_DAYS chunks the window spans (1 = default).
 * @param today - injectable for determinism.
 * @returns inclusive `{from, to}` date strings (`to` is always today).
 */
export function windowForSteps(steps: number, today: Date = new Date()): DateWindow {
    const to = toISODate(today);
    const start = new Date(today);
    start.setDate(start.getDate() - (Math.max(1, steps) * STEP_DAYS - 1));
    return { from: toISODate(start), to };
}

/**
 * Human, condensed day heading (spec §11.2): `MON 02 JUN` / ru `ПН 08 ИЮН`,
 * upper, tabular — weekday/month via Intl (GYM-109), uppercased per locale.
 * The full year is appended only when it differs from the current year.
 *
 * @param iso - the API date string (YYYY-MM-DD).
 * @param today - injectable for determinism.
 * @param locale - explicit locale for deterministic tests; defaults to the
 *   active Telegram locale.
 */
export function formatDayHeading(
    iso: string,
    today: Date = new Date(),
    locale: Locale = getLocale(),
): string {
    const [y, m, d] = iso.split("-").map(Number);
    if (!y || !m || !d) return iso;
    // Construct as local midnight so the weekday matches the calendar date.
    const date = new Date(y, m - 1, d);
    const wd = shortWeekday(date, locale).toLocaleUpperCase(locale);
    const mon = shortMonthInDate(date, locale).toLocaleUpperCase(locale);
    const day = String(d).padStart(2, "0");
    const base = `${wd} ${day} ${mon}`;
    return y === today.getFullYear() ? base : `${base} ${y}`;
}
