/**
 * Unit tests for the pure History window/date model (GYM-124).
 * All date inputs are injected — no reliance on the wall clock.
 */
import { describe, expect, it } from "vitest";
import {
    STEP_DAYS,
    formatDayHeading,
    toISODate,
    windowForSteps,
} from "./historyWindow";

describe("toISODate", () => {
    it("formats a local date as YYYY-MM-DD with zero padding", () => {
        expect(toISODate(new Date(2026, 0, 5))).toBe("2026-01-05");
    });

    it("uses LOCAL components, not UTC (no off-by-one near midnight)", () => {
        // 00:30 local on the 5th: toISOString() would shift to the 4th in any
        // timezone east of UTC; the local formatter must not.
        expect(toISODate(new Date(2026, 5, 5, 0, 30))).toBe("2026-06-05");
        // 23:30 local: west-of-UTC zones would shift forward via toISOString().
        expect(toISODate(new Date(2026, 5, 5, 23, 30))).toBe("2026-06-05");
    });

    it("pads single-digit months and days", () => {
        expect(toISODate(new Date(2026, 8, 9))).toBe("2026-09-09");
    });
});

describe("windowForSteps", () => {
    const today = new Date(2026, 5, 12); // Fri 2026-06-12

    it("returns to = today and an inclusive 84-day window for steps=1", () => {
        const w = windowForSteps(1, today);
        expect(w.to).toBe("2026-06-12");
        // 84 days inclusive: from = today - 83 days.
        expect(w.from).toBe("2026-03-21");
    });

    it("expands backward by STEP_DAYS per extra step, keeping the same to", () => {
        const one = windowForSteps(1, today);
        const two = windowForSteps(2, today);
        expect(two.to).toBe(one.to);
        const spanDays =
            (new Date(two.to).getTime() - new Date(two.from).getTime()) /
                86_400_000 +
            1;
        expect(spanDays).toBe(2 * STEP_DAYS);
    });

    it("clamps steps below 1 to the default window", () => {
        expect(windowForSteps(0, today)).toEqual(windowForSteps(1, today));
        expect(windowForSteps(-3, today)).toEqual(windowForSteps(1, today));
    });

    it("crosses a year boundary correctly", () => {
        const w = windowForSteps(1, new Date(2026, 0, 10)); // 2026-01-10
        expect(w.from).toBe("2025-10-19"); // 83 days back, into the prior year
        expect(w.to).toBe("2026-01-10");
    });
});

describe("formatDayHeading", () => {
    const today = new Date(2026, 5, 12); // year 2026 is "current"

    it("formats a current-year date as WD DD MON without the year", () => {
        // 2026-06-08 is a Monday.
        expect(formatDayHeading("2026-06-08", today, "en")).toBe("MON 08 JUN");
    });

    it("pads single-digit days", () => {
        // 2026-06-03 is a Wednesday.
        expect(formatDayHeading("2026-06-03", today, "en")).toBe("WED 03 JUN");
    });

    it("appends the year only when it differs from the current year", () => {
        // 2025-12-31 is a Wednesday.
        expect(formatDayHeading("2025-12-31", today, "en")).toBe(
            "WED 31 DEC 2025",
        );
    });

    it("localizes the heading via Intl for ru (GYM-109)", () => {
        // Same condensed shape, Russian weekday/month, uppercased, no dot.
        expect(formatDayHeading("2026-06-08", today, "ru")).toBe("ПН 08 ИЮН");
        expect(formatDayHeading("2025-12-31", today, "ru")).toBe(
            "СР 31 ДЕК 2025",
        );
    });

    it("returns the raw input for non-date strings", () => {
        expect(formatDayHeading("not-a-date", today, "en")).toBe("not-a-date");
        expect(formatDayHeading("", today, "en")).toBe("");
    });

    it("returns the raw input for zeroed date parts", () => {
        expect(formatDayHeading("2026-00-10", today, "en")).toBe("2026-00-10");
        expect(formatDayHeading("2026-06-00", today, "en")).toBe("2026-06-00");
    });
});
