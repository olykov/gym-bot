/**
 * Pure render model for the Dashboard THIS WEEK card (GYM-136) — mirrors the
 * activityGridModel/historyWindow pattern: all decisions are computed here so
 * the component is pure markup and the logic is unit-testable.
 *
 * Modes:
 *  - "hidden":     both weeks are all-zero → the card renders nothing (no
 *                  empty noise; the Dashboard's new-user path never mounts
 *                  the card at all, this covers the "trained long ago" case).
 *  - "first-week": last week all-zero AND this week has data → show the
 *                  totals line without a delta line (there is nothing honest
 *                  to compare against).
 *  - "compare":    both lines; per-metric deltas follow the GYM-132 restraint
 *                  rule — a zero delta is omitted (never "▲ 0"), so an even
 *                  week simply shows no figure for that metric.
 */
import type { WeekCompare } from "@/api/analytics";

/** One metric's movement vs last week ("eq" renders nothing — restraint). */
export interface WeekDelta {
    kind: "up" | "down" | "eq";
    /** Absolute movement, already rounded (volume to 0.1, sets integer). */
    amount: number;
}

export interface WeekCompareModel {
    kind: "hidden" | "first-week" | "compare";
    /** This week's totals (the headline line). */
    sets: number;
    volume: number;
    /** Deltas vs last week — present only in "compare" mode. */
    setsDelta?: WeekDelta;
    volumeDelta?: WeekDelta;
}

/** Classify a numeric movement; volume is rounded to one decimal (×2.5kg). */
function toDelta(current: number, previous: number, decimals: number): WeekDelta {
    const factor = 10 ** decimals;
    const amount = Math.round(Math.abs(current - previous) * factor) / factor;
    if (amount === 0) return { kind: "eq", amount: 0 };
    return { kind: current > previous ? "up" : "down", amount };
}

/**
 * Build the THIS WEEK card model from the contract payload.
 *
 * @param wc - the `GET /analytics/week-compare` response.
 * @returns The render model (see module doc for the mode rules).
 */
export function buildWeekCompareModel(wc: WeekCompare): WeekCompareModel {
    const thisEmpty = wc.this_week.sets === 0 && wc.this_week.volume === 0;
    const lastEmpty = wc.last_week.sets === 0 && wc.last_week.volume === 0;

    if (thisEmpty && lastEmpty) {
        return { kind: "hidden", sets: 0, volume: 0 };
    }
    if (lastEmpty) {
        return {
            kind: "first-week",
            sets: wc.this_week.sets,
            volume: wc.this_week.volume,
        };
    }
    return {
        kind: "compare",
        sets: wc.this_week.sets,
        volume: wc.this_week.volume,
        setsDelta: toDelta(wc.this_week.sets, wc.last_week.sets, 0),
        volumeDelta: toDelta(wc.this_week.volume, wc.last_week.volume, 1),
    };
}
