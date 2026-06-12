/**
 * GYM-135 — unit tests for the sparkline geometry + trend-direction helpers.
 * Pure module, no DOM: the render rules (≥3 points or nothing), normalization
 * edges (flat series, single dominant range) and the ±1% flat band are the
 * contract the TrendSparkline component relies on.
 */
import { describe, expect, it } from "vitest";
import {
    buildSparklineGeometry,
    trendDirection,
    MIN_TREND_POINTS,
    SPARKLINE_HEIGHT,
    SPARKLINE_WIDTH,
} from "./trend";

/** Parse a polyline `points` attr back into vertex objects. */
function parsePoints(points: string): { x: number; y: number }[] {
    return points.split(" ").map((pair) => {
        const [x = "", y = ""] = pair.split(",");
        return { x: Number(x), y: Number(y) };
    });
}

describe("buildSparklineGeometry", () => {
    it("returns null below the minimum point count (render nothing)", () => {
        expect(buildSparklineGeometry([])).toBeNull();
        expect(buildSparklineGeometry([100])).toBeNull();
        expect(buildSparklineGeometry([100, 105])).toBeNull();
        expect(MIN_TREND_POINTS).toBe(3);
    });

    it("builds geometry at exactly the minimum point count", () => {
        const geometry = buildSparklineGeometry([100, 102, 104]);
        expect(geometry).not.toBeNull();
        expect(parsePoints(geometry!.points)).toHaveLength(3);
    });

    it("keeps every vertex inside the viewBox (padded)", () => {
        const geometry = buildSparklineGeometry([80, 120, 95, 130, 100]);
        for (const p of parsePoints(geometry!.points)) {
            expect(p.x).toBeGreaterThanOrEqual(0);
            expect(p.x).toBeLessThanOrEqual(SPARKLINE_WIDTH);
            expect(p.y).toBeGreaterThanOrEqual(0);
            expect(p.y).toBeLessThanOrEqual(SPARKLINE_HEIGHT);
        }
    });

    it("spaces x by index across the width, first to last edge", () => {
        const geometry = buildSparklineGeometry([1, 2, 3, 4, 5]);
        const pts = parsePoints(geometry!.points);
        const xs = pts.map((p) => p.x);
        // Monotonic, evenly spaced, spanning the padded width.
        expect(xs[0]).toBeLessThan(xs[4]!);
        const step = xs[1]! - xs[0]!;
        for (let i = 1; i < xs.length; i++) {
            expect(xs[i]! - xs[i - 1]!).toBeCloseTo(step, 1);
        }
    });

    it("maps min to the bottom and max to the top (y inverted)", () => {
        const geometry = buildSparklineGeometry([100, 150, 125]);
        const [low, high, mid] = parsePoints(geometry!.points);
        expect(low!.y).toBeGreaterThan(high!.y); // min sits LOWER on screen
        expect(mid!.y).toBeGreaterThan(high!.y);
        expect(mid!.y).toBeLessThan(low!.y);
    });

    it("normalization edge: a single-value range draws a flat mid line", () => {
        const geometry = buildSparklineGeometry([100, 100, 100, 100]);
        for (const p of parsePoints(geometry!.points)) {
            expect(p.y).toBe(SPARKLINE_HEIGHT / 2);
        }
    });

    it("exposes the last vertex for the end-dot", () => {
        const geometry = buildSparklineGeometry([100, 110, 120]);
        const pts = parsePoints(geometry!.points);
        expect(geometry!.last).toEqual(pts[pts.length - 1]);
    });

    it("duplicate dates are a non-issue: x is index-based by design", () => {
        // Two sessions normalized to the same calendar date still get
        // distinct x positions — the helper never looks at dates at all.
        const values = [100, 101, 101, 102]; // e.g. 2nd and 3rd share a date
        const geometry = buildSparklineGeometry(values);
        const xs = parsePoints(geometry!.points).map((p) => p.x);
        expect(new Set(xs).size).toBe(values.length);
    });
});

describe("trendDirection", () => {
    it("returns null below the minimum point count", () => {
        expect(trendDirection([])).toBeNull();
        expect(trendDirection([100])).toBeNull();
        expect(trendDirection([100, 120])).toBeNull();
    });

    it("up when last beats first by more than 1%", () => {
        expect(trendDirection([100, 90, 108])).toBe("up");
        expect(trendDirection([100, 100, 101.1])).toBe("up");
    });

    it("down when last trails first by more than 1%", () => {
        expect(trendDirection([100, 110, 92])).toBe("down");
        expect(trendDirection([100, 100, 98.9])).toBe("down");
    });

    it("flat inside the ±1% band — boundary values included", () => {
        expect(trendDirection([100, 120, 100])).toBe("flat");
        expect(trendDirection([100, 90, 101])).toBe("flat"); // exactly +1%
        expect(trendDirection([100, 110, 99])).toBe("flat"); // exactly −1%
    });

    it("only the window endpoints matter, not the middle", () => {
        expect(trendDirection([100, 999, 100])).toBe("flat");
        expect(trendDirection([100, 1, 110])).toBe("up");
    });

    it("degenerate zero first value cannot divide: growth is up, else flat", () => {
        expect(trendDirection([0, 0, 50])).toBe("up");
        expect(trendDirection([0, 0, 0])).toBe("flat");
    });
});
