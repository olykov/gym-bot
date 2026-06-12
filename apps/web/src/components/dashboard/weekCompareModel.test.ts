/**
 * Unit tests for the THIS WEEK card render model (GYM-136).
 *
 * Locks the mode rules (hidden / first-week / compare), the delta
 * directions, and the rounding (sets integer, volume to one decimal).
 */
import { describe, expect, it } from "vitest";
import type { WeekCompare } from "@/api/analytics";
import { buildWeekCompareModel } from "./weekCompareModel";

function wc(
    thisWeek: { sets: number; volume: number },
    lastWeek: { sets: number; volume: number },
): WeekCompare {
    return { this_week: thisWeek, last_week: lastWeek };
}

describe("buildWeekCompareModel — modes", () => {
    it("both weeks zero → hidden (the card renders nothing)", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 0, volume: 0 }, { sets: 0, volume: 0 }),
        );
        expect(model.kind).toBe("hidden");
    });

    it("first-ever week (last zero, this has data) → no delta line", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 5, volume: 1200 }, { sets: 0, volume: 0 }),
        );
        expect(model.kind).toBe("first-week");
        expect(model.sets).toBe(5);
        expect(model.volume).toBe(1200);
        expect(model.setsDelta).toBeUndefined();
        expect(model.volumeDelta).toBeUndefined();
    });

    it("this week zero but last week trained → compare (down deltas)", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 0, volume: 0 }, { sets: 8, volume: 2000 }),
        );
        expect(model.kind).toBe("compare");
        expect(model.setsDelta).toEqual({ kind: "down", amount: 8 });
        expect(model.volumeDelta).toEqual({ kind: "down", amount: 2000 });
    });
});

describe("buildWeekCompareModel — deltas", () => {
    it("up deltas carry the positive movement", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 24, volume: 5840 }, { sets: 21, volume: 5420 }),
        );
        expect(model.kind).toBe("compare");
        expect(model.setsDelta).toEqual({ kind: "up", amount: 3 });
        expect(model.volumeDelta).toEqual({ kind: "up", amount: 420 });
    });

    it("equal metrics are eq (the card omits them — never '▲ 0')", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 10, volume: 2500 }, { sets: 10, volume: 2500 }),
        );
        expect(model.setsDelta).toEqual({ kind: "eq", amount: 0 });
        expect(model.volumeDelta).toEqual({ kind: "eq", amount: 0 });
    });

    it("mixed direction: sets up, volume down", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 12, volume: 1800 }, { sets: 10, volume: 2000 }),
        );
        expect(model.setsDelta).toEqual({ kind: "up", amount: 2 });
        expect(model.volumeDelta).toEqual({ kind: "down", amount: 200 });
    });

    it("volume rounds to one decimal (×2.5kg half-kilo artifacts)", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 4, volume: 1000.25 }, { sets: 4, volume: 1000 }),
        );
        // 0.25 rounds to 0.3 — a real movement, kept (kind up).
        expect(model.volumeDelta).toEqual({ kind: "up", amount: 0.3 });
    });

    it("sub-0.05 volume drift rounds away to eq", () => {
        const model = buildWeekCompareModel(
            wc({ sets: 4, volume: 1000.04 }, { sets: 4, volume: 1000 }),
        );
        expect(model.volumeDelta).toEqual({ kind: "eq", amount: 0 });
    });
});
