/**
 * GYM-135 — the e1RM micro-sparkline + trend chip for the SetLogger heading
 * row (concept doc 03 §4.2): "where is this exercise's curve going?".
 *
 * Self-contained container: it owns the `useExerciseTrend` read, so mounting
 * it (Phase B only) is what fires the query alongside log-context — the
 * steppers never wait on it. While loading, on error, or with fewer than 3
 * points in the window it renders NOTHING (deliberate deviation from the
 * task-file "skeleton = flat hint line": a placeholder that may resolve to
 * nothing is flicker, absence is the quiet state).
 *
 * Strictly secondary visual weight: a 64×20 accent polyline (no axes, just a
 * 2px end-dot) + a tiny text chip — `▲ 8w` accent when up, `▼/→` in --hint.
 * The SVG and chip glyphs are aria-hidden; the group exposes a full-sentence
 * `aria-label` (role="img") as the accessible alternative.
 */
import { useMemo } from "react";
import { useT } from "@/i18n/catalog";
import { useExerciseTrend, TREND_WEEKS } from "@/hooks/useRecord";
import {
    buildSparklineGeometry,
    trendDirection,
    SPARKLINE_HEIGHT,
    SPARKLINE_WIDTH,
    type TrendDirection,
} from "./trend";

/** Chip label key per direction (catalog-typed, GYM-109). */
const CHIP_KEY = {
    up: "trend.up",
    down: "trend.down",
    flat: "trend.flat",
} as const satisfies Record<TrendDirection, string>;

/** Accessible-sentence key per direction. */
const ARIA_KEY = {
    up: "trend.upAria",
    down: "trend.downAria",
    flat: "trend.flatAria",
} as const satisfies Record<TrendDirection, string>;

interface TrendSparklineProps {
    /** Canonical muscle name (query key part). */
    muscle: string;
    /** Exercise name (query key part). */
    exercise: string;
}

export function TrendSparkline({ muscle, exercise }: TrendSparklineProps) {
    const { t } = useT();
    const trend = useExerciseTrend(muscle, exercise);

    const values = useMemo(
        () => (trend.data?.e1rm_trend ?? []).map((p) => p.e1rm),
        [trend.data],
    );
    const geometry = useMemo(() => buildSparklineGeometry(values), [values]);
    const direction = trendDirection(values);

    // <3 points in the window, still loading, or errored → nothing (quiet).
    if (geometry === null || direction === null) return null;

    return (
        <span
            role="img"
            aria-label={t(ARIA_KEY[direction], { weeks: TREND_WEEKS })}
            className="flex shrink-0 items-center gap-1.5"
        >
            <svg
                viewBox={`0 0 ${SPARKLINE_WIDTH} ${SPARKLINE_HEIGHT}`}
                width={SPARKLINE_WIDTH}
                height={SPARKLINE_HEIGHT}
                aria-hidden="true"
                className="shrink-0"
            >
                <polyline
                    points={geometry.points}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <circle
                    cx={geometry.last.x}
                    cy={geometry.last.y}
                    r="2"
                    fill="var(--accent)"
                />
            </svg>
            <span
                aria-hidden="true"
                className={`whitespace-nowrap text-label ${
                    direction === "up" ? "text-accent" : "text-hint"
                }`}
            >
                {t(CHIP_KEY[direction], { weeks: TREND_WEEKS })}
            </span>
        </span>
    );
}
