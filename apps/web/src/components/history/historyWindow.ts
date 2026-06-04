/**
 * Pure date model for the History day-list window-based pagination (spec §11.2)
 * — no React, no DOM. Mirrors the activity grid's window discipline: the list
 * paginates by an expanding `from`/`to` window, never by offset/limit.
 *
 * v1 default window = the last ~12 weeks (84 days). "Load earlier" expands the
 * window backward another step (same `to`, `from -= STEP_DAYS`) so a multi-year
 * history never loads as one unbounded list (the §0/ARCH §2 anti-pattern).
 */

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

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
const MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
];

/**
 * Human, condensed day heading (spec §11.2): `MON 02 JUN`, upper, tabular. The
 * full year is appended only when it differs from the current year.
 *
 * @param iso - the API date string (YYYY-MM-DD).
 * @param today - injectable for determinism.
 */
export function formatDayHeading(iso: string, today: Date = new Date()): string {
    const [y, m, d] = iso.split("-").map(Number);
    if (!y || !m || !d) return iso;
    // Construct as local midnight so the weekday matches the calendar date.
    const date = new Date(y, m - 1, d);
    const wd = WEEKDAYS[date.getDay()];
    const mon = MONTHS[date.getMonth()];
    const day = String(d).padStart(2, "0");
    const base = `${wd} ${day} ${mon}`;
    return y === today.getFullYear() ? base : `${base} ${y}`;
}
