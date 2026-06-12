/**
 * Unit tests for the pure activity-grid model (GYM-124).
 * `today` is injected everywhere — deterministic, no wall clock.
 */
import { describe, expect, it } from "vitest";
import type { ActivityDay } from "@/api/analytics";
import {
    WEEKS,
    buildGrid,
    cellDetailText,
    cellTooltip,
    levelFor,
    monthLabels,
    windowRange,
    type GridCell,
} from "./activityGridModel";

// Wed 2026-06-10: this week's Monday is 2026-06-08; Thu..Sun are future.
const TODAY = new Date(2026, 5, 10);

describe("levelFor", () => {
    it("buckets set counts into the 0..4 ramp", () => {
        expect(levelFor(0)).toBe(0);
        expect(levelFor(-1)).toBe(0);
        expect(levelFor(1)).toBe(1);
        expect(levelFor(3)).toBe(1);
        expect(levelFor(4)).toBe(2);
        expect(levelFor(7)).toBe(2);
        expect(levelFor(8)).toBe(3);
        expect(levelFor(12)).toBe(3);
        expect(levelFor(13)).toBe(4);
        expect(levelFor(100)).toBe(4);
    });
});

describe("windowRange", () => {
    it("starts on the Monday WEEKS-1 weeks before this week's Monday", () => {
        const { from, to } = windowRange(TODAY);
        expect(to).toBe("2026-06-10");
        // 2026-06-08 (this Monday) - 25 weeks = 2025-12-15, a Monday.
        expect(from).toBe("2025-12-15");
        expect(new Date(`${from}T00:00:00`).getDay()).toBe(1); // Monday
    });
});

describe("buildGrid", () => {
    it("returns WEEKS columns of 7 cells each", () => {
        const grid = buildGrid([], TODAY);
        expect(grid).toHaveLength(WEEKS);
        for (const week of grid) expect(week).toHaveLength(7);
    });

    it("is Monday-first: the first cell of every column is a Monday", () => {
        const grid = buildGrid([], TODAY);
        expect(grid[0][0].date).toBe("2025-12-15");
        for (const week of grid) {
            const first = week[0].date;
            if (first) {
                expect(new Date(`${first}T00:00:00`).getDay()).toBe(1);
            }
        }
    });

    it("renders future days of the current week as padding cells", () => {
        const grid = buildGrid([], TODAY);
        const lastWeek = grid[WEEKS - 1];
        // Mon 08, Tue 09, Wed 10 (today) are real; Thu 11..Sun 14 are padding.
        expect(lastWeek[0].date).toBe("2026-06-08");
        expect(lastWeek[2].date).toBe("2026-06-10");
        for (const cell of lastWeek.slice(3)) {
            expect(cell.date).toBeNull();
            expect(cell.sets).toBe(0);
            expect(cell.level).toBe(0);
        }
    });

    it("marks exactly one cell as today", () => {
        const grid = buildGrid([], TODAY);
        const todayCells = grid.flat().filter((c) => c.isToday);
        expect(todayCells).toHaveLength(1);
        expect(todayCells[0].date).toBe("2026-06-10");
    });

    it("maps API day counts onto the right cells with bucketed levels", () => {
        const days: ActivityDay[] = [
            { date: "2026-06-08", sets_count: 2 },
            { date: "2026-06-10", sets_count: 9 },
        ];
        const grid = buildGrid(days, TODAY);
        const lastWeek = grid[WEEKS - 1];
        expect(lastWeek[0]).toMatchObject({ date: "2026-06-08", sets: 2, level: 1 });
        expect(lastWeek[2]).toMatchObject({ date: "2026-06-10", sets: 9, level: 3 });
        // Untouched day in the window stays empty.
        expect(lastWeek[1]).toMatchObject({ date: "2026-06-09", sets: 0, level: 0 });
    });
});

describe("monthLabels (GYM-123)", () => {
    /** Minimal synthetic column: only the first (Monday) cell's date matters. */
    const col = (date: string | null): GridCell[] => [
        { date, sets: 0, level: 0, isToday: false },
    ];

    it("labels each column whose month differs from the previous column's", () => {
        const labels = monthLabels(buildGrid([], TODAY), "en");
        expect(labels).toHaveLength(WEEKS);
        // Window Mondays: 2025-12-15 … 2026-06-08 (see windowRange test).
        const expected: Array<string | null> = new Array(WEEKS).fill(null);
        expected[3] = "Jan"; // 2026-01-05
        expected[7] = "Feb"; // 2026-02-02
        expected[11] = "Mar"; // 2026-03-02
        expected[16] = "Apr"; // 2026-04-06
        expected[20] = "May"; // 2026-05-04
        expected[24] = "Jun"; // 2026-06-01
        expect(labels).toEqual(expected);
    });

    it("never labels the first column (no previous month to differ from)", () => {
        const labels = monthLabels(buildGrid([], TODAY), "en");
        expect(labels[0]).toBeNull();
    });

    it("skips labels closer than the min gap to the previous label", () => {
        const columns = [
            col("2026-01-05"),
            col("2026-02-02"), // change → labelled
            col("2026-03-02"), // change but only 1 col after Feb → skipped
            col("2026-04-06"), // change but only 2 cols after Feb → skipped
        ];
        expect(monthLabels(columns, "en")).toEqual([null, "Feb", null, null]);
    });

    it("localizes month labels via Intl for ru (GYM-109)", () => {
        const columns = [col("2026-01-05"), col("2026-02-02")];
        expect(monthLabels(columns, "ru")).toEqual([null, "Февр"]);
    });

    it("treats padding-first columns as unlabelled", () => {
        expect(monthLabels([col(null), col(null)], "en")).toEqual([null, null]);
    });

    it("returns an empty array for no columns", () => {
        expect(monthLabels([], "en")).toEqual([]);
    });
});

describe("cellTooltip", () => {
    it("returns undefined for padding cells", () => {
        expect(
            cellTooltip({ date: null, sets: 0, level: 0, isToday: false }, "en"),
        ).toBeUndefined();
    });

    it("uses the singular noun for exactly one set", () => {
        expect(
            cellTooltip(
                { date: "2026-06-08", sets: 1, level: 1, isToday: false },
                "en",
            ),
        ).toBe("1 set on 2026-06-08");
    });

    it("uses the plural noun otherwise (including zero)", () => {
        expect(
            cellTooltip(
                { date: "2026-06-08", sets: 5, level: 2, isToday: false },
                "en",
            ),
        ).toBe("5 sets on 2026-06-08");
        expect(
            cellTooltip(
                { date: "2026-06-09", sets: 0, level: 0, isToday: false },
                "en",
            ),
        ).toBe("0 sets on 2026-06-09");
    });

    it("localizes via the catalog plural rules for ru (GYM-109)", () => {
        expect(
            cellTooltip(
                { date: "2026-06-08", sets: 5, level: 2, isToday: false },
                "ru",
            ),
        ).toBe("5 сетов — 2026-06-08");
    });
});

describe("cellDetailText (GYM-117)", () => {
    it("returns null for padding cells", () => {
        expect(
            cellDetailText(
                { date: null, sets: 0, level: 0, isToday: false },
                TODAY,
                "en",
            ),
        ).toBeNull();
    });

    it("formats `N sets · <day heading>` in the History heading format", () => {
        // 2026-06-08 is a Monday.
        expect(
            cellDetailText(
                { date: "2026-06-08", sets: 12, level: 3, isToday: false },
                TODAY,
                "en",
            ),
        ).toBe("12 sets · MON 08 JUN");
    });

    it("uses the singular noun for exactly one set", () => {
        expect(
            cellDetailText(
                { date: "2026-06-09", sets: 1, level: 1, isToday: false },
                TODAY,
                "en",
            ),
        ).toBe("1 set · TUE 09 JUN");
    });

    it("shows zero sets for empty (but real) days", () => {
        expect(
            cellDetailText(
                { date: "2026-06-07", sets: 0, level: 0, isToday: false },
                TODAY,
                "en",
            ),
        ).toBe("0 sets · SUN 07 JUN");
    });

    it("appends the year when it differs from the current year", () => {
        expect(
            cellDetailText(
                { date: "2025-12-15", sets: 3, level: 1, isToday: false },
                TODAY,
                "en",
            ),
        ).toBe("3 sets · MON 15 DEC 2025");
    });

    it("localizes the whole line for ru (GYM-109)", () => {
        expect(
            cellDetailText(
                { date: "2026-06-08", sets: 12, level: 3, isToday: false },
                TODAY,
                "ru",
            ),
        ).toBe("12 сетов · ПН 08 ИЮН");
    });
});
