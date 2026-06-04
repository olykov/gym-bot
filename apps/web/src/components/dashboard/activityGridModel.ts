/**
 * Pure date/layout model for the activity grid (spec §10.2) — no React, no DOM.
 *
 * Builds a Monday-first, 7×N matrix of cells for the MVP window (last ~26 weeks)
 * from the `/analytics/activity` day counts. Keeping this pure makes the 360px
 * fit and the Monday-first ordering testable and keeps the component thin.
 */
import type { ActivityDay } from "@/api/analytics";

/** MVP window: ~26 weeks (6 months) — fits 360px with no horizontal scroll. */
export const WEEKS = 26;

export interface GridCell {
    /** YYYY-MM-DD, or null for padding cells before the first column starts. */
    date: string | null;
    sets: number;
    /** 0 = empty, 1..4 = intensity bucket (the chalk→iron ramp). */
    level: 0 | 1 | 2 | 3 | 4;
    isToday: boolean;
}

/** Local YYYY-MM-DD (avoids UTC off-by-one from toISOString). */
export function toISODate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

/** Monday-first weekday index (Mon=0 … Sun=6). */
function mondayIndex(d: Date): number {
    return (d.getDay() + 6) % 7;
}

/** The inclusive [from, to] date strings for the MVP query window. */
export function windowRange(today: Date = new Date()): { from: string; to: string } {
    const to = new Date(today);
    // Start = the Monday WEEKS-1 weeks before this week's Monday.
    const start = new Date(today);
    start.setDate(start.getDate() - mondayIndex(today) - (WEEKS - 1) * 7);
    return { from: toISODate(start), to: toISODate(to) };
}

/** Bucket a per-day set count into the 4-level ramp (0 = no activity). */
export function levelFor(sets: number): GridCell["level"] {
    if (sets <= 0) return 0;
    if (sets <= 3) return 1;
    if (sets <= 7) return 2;
    if (sets <= 12) return 3;
    return 4;
}

/**
 * Build the column-major grid (each column = one Mon→Sun week).
 *
 * @param days - activity rows from the API (only active days are present).
 * @param today - injectable for determinism in tests.
 * @returns WEEKS columns of 7 cells, Monday-first, ending at `today`.
 */
export function buildGrid(days: ActivityDay[], today: Date = new Date()): GridCell[][] {
    const counts = new Map<string, number>();
    for (const d of days) counts.set(d.date, d.sets_count);

    const todayIso = toISODate(today);

    // First cell = the Monday of the earliest visible week.
    const start = new Date(today);
    start.setDate(start.getDate() - mondayIndex(today) - (WEEKS - 1) * 7);
    start.setHours(0, 0, 0, 0);

    const columns: GridCell[][] = [];
    const cursor = new Date(start);

    for (let col = 0; col < WEEKS; col++) {
        const week: GridCell[] = [];
        for (let row = 0; row < 7; row++) {
            const iso = toISODate(cursor);
            // Future days in the current (last) week render as padding.
            const isFuture = iso > todayIso;
            const sets = counts.get(iso) ?? 0;
            week.push({
                date: isFuture ? null : iso,
                sets: isFuture ? 0 : sets,
                level: isFuture ? 0 : levelFor(sets),
                isToday: iso === todayIso,
            });
            cursor.setDate(cursor.getDate() + 1);
        }
        columns.push(week);
    }
    return columns;
}

/** Tooltip text for a cell (spec §10.2: "N sets on <date>"). */
export function cellTooltip(cell: GridCell): string | undefined {
    if (!cell.date) return undefined;
    const noun = cell.sets === 1 ? "set" : "sets";
    return `${cell.sets} ${noun} on ${cell.date}`;
}
