/**
 * e1RM — estimated one-rep max via the Epley formula (GYM-133, doc 03 §4.1).
 *
 * Pure, no React/DOM. Shared by the Progress chart's "e1RM" mode and the
 * SetLogger PR-type resolver (derive.ts). Client-side by design: GYM-134
 * later adds a server-computed trend endpoint; until then everything here
 * derives from data the client already has.
 */
import type { ExerciseProgress } from "@/api/analytics";

/**
 * Epley estimated 1RM: `weight × (1 + reps/30)`.
 *
 * Edge (defined + tested): `reps <= 0` returns the weight itself — a zero-rep
 * entry carries no rep bonus, and the formula must never DEFLATE the weight.
 * Returns the raw (unrounded) value — round only at display time via
 * {@link roundE1rm} so comparisons stay exact.
 */
export function epley(weight: number, reps: number): number {
    if (reps <= 0) return weight;
    return weight * (1 + reps / 30);
}

/** Display rounding for e1RM values: 1 decimal (e.g. 126.66… → 126.7). */
export function roundE1rm(value: number): number {
    return Math.round(value * 10) / 10;
}

/** The best (max-e1RM) set of one session date, with its source weight×reps. */
export interface E1rmDayBest {
    /** Display-rounded e1RM (1 decimal) — the plotted value. */
    e1rm: number;
    /** The weight of the set that produced the max e1RM. */
    weight: number;
    /** The reps of that set. */
    reps: number;
}

/**
 * Per session date: the MAX e1RM across that day's sets (GYM-133) — mirrors
 * the chart's "By Weight" client derivation (max weight per date), keyed by
 * ms-epoch date exactly like `distinctSortedDates`.
 *
 * The contract (`ExercisePoint`) requires `reps` on every point, so every
 * point participates; `epley` handles a degenerate `reps <= 0` honestly
 * (no rep bonus). Comparison uses the RAW e1RM (rounding only for display);
 * on a tie the FIRST encountered set wins (strict `>` replace — same rule as
 * `byWeightSeries`). Points with an unparseable date are skipped.
 */
export function maxE1rmByDate(
    progress: ExerciseProgress,
): Map<number, E1rmDayBest> {
    // Track the raw value for exact comparison; expose the rounded one.
    const rawByDate = new Map<number, number>();
    const bestByDate = new Map<number, E1rmDayBest>();
    for (const s of progress.series) {
        for (const p of s.points) {
            const ms = new Date(p.date).getTime();
            if (Number.isNaN(ms)) continue;
            const raw = epley(p.weight, p.reps);
            const prevRaw = rawByDate.get(ms);
            if (prevRaw === undefined || raw > prevRaw) {
                rawByDate.set(ms, raw);
                bestByDate.set(ms, {
                    e1rm: roundE1rm(raw),
                    weight: p.weight,
                    reps: p.reps,
                });
            }
        }
    }
    return bestByDate;
}
