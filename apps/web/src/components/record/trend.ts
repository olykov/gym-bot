/**
 * GYM-135 — pure geometry/derivation helpers for the SetLogger e1RM trend
 * sparkline (concept doc 03 §4.2). No React/DOM; unit-tested in trend.test.ts.
 *
 * Input everywhere is the plain e1RM value series (date-ascending, as the
 * `e1rm_trend` contract guarantees). X spacing is INDEX-based, not date-based:
 * the sparkline is a "direction of travel" glyph, not a chart — equal spacing
 * keeps it readable when sessions are irregular, and makes duplicate dates a
 * non-issue (each point gets its own x).
 *
 * Render rule (both helpers agree): fewer than {@link MIN_TREND_POINTS}
 * points → `null` → the caller renders NOTHING. Absence is the quiet state.
 */

/** Sparkline viewBox width (px units of the SVG coordinate space). */
export const SPARKLINE_WIDTH = 64;
/** Sparkline viewBox height. */
export const SPARKLINE_HEIGHT = 20;
/** Minimum points in the window for the trend to render at all (spec). */
export const MIN_TREND_POINTS = 3;

/** Inset so the 1.5 stroke and the 2px end-dot never clip at the edges. */
const PADDING = 2.5;
/** Relative last-vs-first change below which the trend reads as flat (±1%). */
const FLAT_THRESHOLD = 0.01;

/** One normalized sparkline vertex in viewBox coordinates. */
export interface SparklinePoint {
    x: number;
    y: number;
}

/** Everything the SVG needs: the polyline `points` attr + the end-dot. */
export interface SparklineGeometry {
    /** Space-separated "x,y" pairs for `<polyline points>`. */
    points: string;
    /** The last vertex — where the 2px end-dot is drawn. */
    last: SparklinePoint;
}

/** Round to 2 decimals — stable, compact SVG attribute strings. */
function round2(value: number): number {
    return Math.round(value * 100) / 100;
}

/**
 * Normalize an e1RM series into the sparkline viewBox.
 *
 * - x: index-spaced across the padded width (see module doc).
 * - y: min→bottom, max→top within the padded height; a zero value range
 *   (all points equal) draws a horizontal mid-line instead of dividing by 0.
 *
 * @param values - e1RM values, date-ascending.
 * @returns the polyline geometry, or null when `values.length < 3`.
 */
export function buildSparklineGeometry(
    values: readonly number[],
): SparklineGeometry | null {
    if (values.length < MIN_TREND_POINTS) return null;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const innerWidth = SPARKLINE_WIDTH - 2 * PADDING;
    const innerHeight = SPARKLINE_HEIGHT - 2 * PADDING;
    const step = innerWidth / (values.length - 1);

    const vertices = values.map((value, i) => ({
        x: round2(PADDING + i * step),
        y:
            range === 0
                ? SPARKLINE_HEIGHT / 2
                : round2(PADDING + (1 - (value - min) / range) * innerHeight),
    }));

    return {
        points: vertices.map((p) => `${p.x},${p.y}`).join(" "),
        // Safe: length >= MIN_TREND_POINTS > 0.
        last: vertices[vertices.length - 1],
    };
}

/** The trend chip direction: ▲ up / ▼ down / → flat. */
export type TrendDirection = "up" | "down" | "flat";

/**
 * Direction of travel over the window: last point vs first point.
 *
 * Relative change beyond ±{@link FLAT_THRESHOLD} (1%) reads as up/down;
 * anything inside the band — including exactly ±1% — is flat. A zero first
 * value (degenerate but defensive) can't divide: any growth is "up", no
 * growth is "flat".
 *
 * @param values - e1RM values, date-ascending.
 * @returns the direction, or null when `values.length < 3` (render nothing).
 */
export function trendDirection(
    values: readonly number[],
): TrendDirection | null {
    if (values.length < MIN_TREND_POINTS) return null;

    const first = values[0];
    const last = values[values.length - 1];
    if (first === 0) return last > 0 ? "up" : "flat";

    const delta = (last - first) / Math.abs(first);
    if (delta > FLAT_THRESHOLD) return "up";
    if (delta < -FLAT_THRESHOLD) return "down";
    return "flat";
}
