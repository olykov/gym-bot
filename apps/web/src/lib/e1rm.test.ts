/**
 * Unit tests for the e1RM math + the chart's e1RM-mode derivation (GYM-133).
 * Encodes the Epley formula, its defined reps<=0 edge, display rounding, and
 * the per-date max derivation that mirrors the chart's By Weight rules
 * (first-wins ties, skipped unparseable dates).
 */
import { describe, expect, it } from "vitest";
import type { ExerciseProgress } from "@/api/analytics";
import { epley, maxE1rmByDate, roundE1rm } from "./e1rm";

function progress(
    ...series: { set: number; points: [string, number, number][] }[]
): ExerciseProgress {
    return {
        series: series.map((s) => ({
            set: s.set,
            points: s.points.map(([date, weight, reps]) => ({
                date,
                weight,
                reps,
            })),
        })),
    };
}

const ms = (date: string): number => new Date(date).getTime();

describe("epley", () => {
    it("computes weight × (1 + reps/30)", () => {
        expect(epley(100, 8)).toBeCloseTo(126.6667, 3);
        expect(epley(102.5, 8)).toBeCloseTo(129.8333, 3);
        expect(epley(30, 30)).toBe(60);
    });

    it("reps 1 adds the single-rep bonus (raw Epley, no special-casing)", () => {
        expect(epley(60, 1)).toBeCloseTo(62, 5);
    });

    it("defined edge: reps 0 (or negative) returns the weight itself", () => {
        expect(epley(100, 0)).toBe(100);
        expect(epley(100, -3)).toBe(100);
    });

    it("more reps at the same weight means a higher e1RM (the whole point)", () => {
        expect(epley(100, 10)).toBeGreaterThan(epley(100, 8));
    });
});

describe("roundE1rm (display rounding, 1 decimal)", () => {
    it("rounds to one decimal", () => {
        expect(roundE1rm(126.66666)).toBe(126.7);
        expect(roundE1rm(129.83333)).toBe(129.8);
        expect(roundE1rm(120)).toBe(120);
    });
});

describe("maxE1rmByDate (chart e1RM mode — mirrors By Weight derivation)", () => {
    it("returns an empty map for an empty series", () => {
        expect(maxE1rmByDate(progress()).size).toBe(0);
    });

    it("takes the max e1RM across a date's sets, carrying the source w×r", () => {
        const p = progress({
            set: 1,
            // 100×8 → 126.67 BEATS 102.5×5 → 119.58: the heavier set is NOT
            // automatically the best — that's why e1RM is its own mode.
            points: [
                ["2026-06-01", 102.5, 5],
                ["2026-06-01", 100, 8],
            ],
        });
        expect(maxE1rmByDate(p).get(ms("2026-06-01"))).toEqual({
            e1rm: 126.7,
            weight: 100,
            reps: 8,
        });
    });

    it("groups across ALL set series per date (flattened like By Weight)", () => {
        const p = progress(
            { set: 1, points: [["2026-06-01", 80, 8]] },
            { set: 2, points: [["2026-06-01", 90, 6], ["2026-06-08", 90, 8]] },
        );
        const best = maxE1rmByDate(p);
        // Day 1: set 2's 90×6 → 108 beats set 1's 80×8 → 101.33.
        expect(best.get(ms("2026-06-01"))).toEqual({
            e1rm: 108,
            weight: 90,
            reps: 6,
        });
        // Day 2: only one set → 90×8 = 114.
        expect(best.get(ms("2026-06-08"))).toEqual({
            e1rm: 114,
            weight: 90,
            reps: 8,
        });
    });

    it("keeps the FIRST encountered set on an exact e1RM tie (strict >)", () => {
        const p = progress({
            set: 1,
            // Both compute to e1RM 120: 100×6 and 112.5×2.
            points: [
                ["2026-06-01", 100, 6],
                ["2026-06-01", 112.5, 2],
            ],
        });
        expect(maxE1rmByDate(p).get(ms("2026-06-01"))).toEqual({
            e1rm: 120,
            weight: 100,
            reps: 6,
        });
    });

    it("compares on the RAW value (rounding is display-only)", () => {
        // Both round to a display value of 117.5, but the second point's RAW
        // e1RM is strictly greater — it must win despite the rounded tie.
        const p = progress({
            set: 1,
            points: [
                ["2026-06-01", 113.7, 1], // raw 117.49 → display 117.5
                ["2026-06-01", 113.75, 1], // raw 117.5417 → display 117.5
            ],
        });
        expect(maxE1rmByDate(p).get(ms("2026-06-01"))).toEqual({
            e1rm: 117.5,
            weight: 113.75,
            reps: 1,
        });
    });

    it("handles the reps-0 edge per epley (no rep bonus)", () => {
        const p = progress({ set: 1, points: [["2026-06-01", 100, 0]] });
        expect(maxE1rmByDate(p).get(ms("2026-06-01"))).toEqual({
            e1rm: 100,
            weight: 100,
            reps: 0,
        });
    });

    it("skips points with an unparseable date (same rule as the chart axis)", () => {
        const p = progress({
            set: 1,
            points: [
                ["not-a-date", 100, 8],
                ["2026-06-01", 80, 8],
            ],
        });
        const best = maxE1rmByDate(p);
        expect(best.size).toBe(1);
        expect(best.get(ms("2026-06-01"))?.weight).toBe(80);
    });
});
