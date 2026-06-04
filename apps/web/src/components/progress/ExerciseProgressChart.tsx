/**
 * Exercise progress chart (spec §10.3, GYM-57) — `echarts-for-react`, weight over
 * time on a shared category axis of the distinct session dates. Two modes:
 *
 *  - **By Weight** (default): ONE line = the max weight logged per session/date —
 *    the strength-over-time trend ("how my bench grew"), derived client-side from
 *    the per-set series (no API change). Each point carries the reps of that day's
 *    heaviest set so the tooltip reads `{weight}kg × {reps}` (GYM-63).
 *  - **By Set**: one line per set number (the original behavior). Reps ride along
 *    in each tooltip row so the chart stays legible at 360px without a second axis.
 *
 * The tooltip shows `{weight}kg × {reps}` plus the full date in BOTH modes; reps
 * rides in each point's `data.reps` (spec §10.5 token theming unchanged).
 *
 * X-axis labels are thinned to ~5 sparse `DD MMM` ticks (GYM-57 §2a); the full
 * date stays in the tooltip. Theming is bound to tokens (spec §10.5) via
 * {@link echartsTheme}: series take the `--accent`→`--hint` ramp, axes/text use
 * `--hint`/`--text` in Sora tabular-nums, the tooltip is `--bg`/`--text`, and
 * beyond the color cap series vary dash style so multi-set is distinguishable
 * without relying on color alone. It re-themes on Telegram `themeChanged`.
 */
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { Card } from "@/components/ui/Card";
import { useThemeVersion } from "@/hooks/useThemeVersion";
import type { ExerciseProgress } from "@/api/analytics";
import {
    baseChartOption,
    formatAxisDate,
    readCssVars,
    seriesColorAt,
    seriesLineStyle,
    sparseLabelIndices,
} from "@/components/charts/echartsTheme";

export type ProgressMode = "weight" | "set";

interface ExerciseProgressChartProps {
    title: string;
    progress: ExerciseProgress;
    /** "weight" = single max-weight-per-date trend; "set" = one line per set. */
    mode: ProgressMode;
}

export function ExerciseProgressChart({
    title,
    progress,
    mode,
}: ExerciseProgressChartProps) {
    // Re-read tokens + rebuild the option whenever Telegram flips light/dark.
    const themeVersion = useThemeVersion();

    const option = useMemo(() => {
        const vars = readCssVars();
        const base = baseChartOption(vars);

        // Shared, sorted, distinct session dates → the category x-axis. Both
        // modes plot onto the same axis so dates align across sets.
        const dates = distinctSortedDates(progress);
        // ms-epoch strings as category values; axis formatter renders `DD MMM`.
        const categories = dates.map((ms) => String(ms));
        const indexOf = new Map(dates.map((ms, i) => [ms, i] as const));

        // Thin to ~5 sparse labels regardless of point count (GYM-57 §2a).
        const keep = sparseLabelIndices(dates.length);

        const series =
            mode === "weight"
                ? [byWeightSeries(progress, dates, vars)]
                : bySetSeries(progress, indexOf, vars);

        return {
            ...base,
            xAxis: {
                ...base.xAxis,
                data: categories,
                axisLabel: {
                    ...base.xAxis.axisLabel,
                    // Render only the sparse picks; blank the rest.
                    formatter: (value: string, index: number) =>
                        keep.has(index) ? formatAxisDate(Number(value)) : "",
                    interval: 0,
                },
            },
            legend:
                mode === "weight"
                    ? { ...base.legend, show: false }
                    : base.legend,
            tooltip: {
                ...base.tooltip,
                // Full date header + per-line `{weight}kg × {reps}` (spec §11.2
                // figure format). Reps rides in each point's `data.reps` in BOTH
                // modes: By Set carries the set's reps; By Weight carries the
                // reps of that date's heaviest set (see {@link byWeightSeries}).
                formatter: (params: TooltipParam[]) => {
                    if (!params.length) return "";
                    const date = formatTooltipDate(params[0].axisValue);
                    const rows = params
                        .map((p) => {
                            const weight = p.value;
                            const reps = p.data?.reps;
                            return `${p.marker}${p.seriesName}: ${weight}kg${
                                reps != null ? ` × ${reps}` : ""
                            }`;
                        })
                        .join("<br/>");
                    return `${date}<br/>${rows}`;
                },
            },
            series,
        };
        // themeVersion intentionally forces a re-read on themeChanged.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [progress, mode, themeVersion]);

    return (
        <Card>
            <div className="mb-3 font-display text-title text-text">{title}</div>
            <ReactECharts
                // Key on theme + mode so ECharts re-inits cleanly on a flip/switch.
                key={`${themeVersion}-${mode}`}
                option={option}
                notMerge
                lazyUpdate
                style={{ height: 256, width: "100%" }}
                opts={{ renderer: "svg" }}
            />
        </Card>
    );
}

/** A category point carrying its reps for the tooltip. `null` = no value on that date. */
interface ChartPoint {
    value: number;
    reps?: number;
}

/** Distinct session dates (ms epoch), ascending, across every set's points. */
function distinctSortedDates(progress: ExerciseProgress): number[] {
    const set = new Set<number>();
    for (const s of progress.series) {
        for (const p of s.points) {
            const ms = new Date(p.date).getTime();
            if (!Number.isNaN(ms)) set.add(ms);
        }
    }
    return [...set].sort((a, b) => a - b);
}

/**
 * By Weight (default): one line = the MAX weight logged per session/date —
 * flatten all sets' points, group by date, take the max weight (GYM-57 §2b).
 *
 * Each derived point also carries the **reps of that max-weight set** so the
 * tooltip can show `{weight}kg × {reps}` for the heaviest set of the day. On a
 * tie (two sets at the same max weight), the FIRST encountered wins — we only
 * replace on a strictly-greater weight (`>`), so the earlier set's reps stay.
 */
function byWeightSeries(
    progress: ExerciseProgress,
    dates: number[],
    vars: ReturnType<typeof readCssVars>,
) {
    // Per date: the max weight and the reps of the set that set it.
    const maxByDate = new Map<number, { weight: number; reps: number }>();
    for (const s of progress.series) {
        for (const p of s.points) {
            const ms = new Date(p.date).getTime();
            if (Number.isNaN(ms)) continue;
            const prev = maxByDate.get(ms);
            // Strict `>` → ties keep the first-encountered set's reps.
            if (prev == null || p.weight > prev.weight) {
                maxByDate.set(ms, { weight: p.weight, reps: p.reps });
            }
        }
    }
    // One value per category slot (null where the date has no point — none here,
    // every date came from the data, but keep it index-aligned).
    const data: Array<ChartPoint | null> = dates.map((ms) => {
        const top = maxByDate.get(ms);
        return top == null ? null : { value: top.weight, reps: top.reps };
    });
    return {
        name: "Max weight",
        type: "line" as const,
        showSymbol: true,
        symbolSize: 6,
        smooth: false,
        connectNulls: true,
        data,
        lineStyle: { color: seriesColorAt(vars, 0), width: 2, ...seriesLineStyle(0) },
        itemStyle: { color: seriesColorAt(vars, 0) },
    };
}

/** By Set: one line per set number, weight per date (the original behavior). */
function bySetSeries(
    progress: ExerciseProgress,
    indexOf: Map<number, number>,
    vars: ReturnType<typeof readCssVars>,
) {
    return progress.series.map((s, i) => {
        const data: Array<ChartPoint | null> = new Array(indexOf.size).fill(null);
        for (const p of s.points) {
            const ms = new Date(p.date).getTime();
            const idx = indexOf.get(ms);
            if (idx != null) data[idx] = { value: p.weight, reps: p.reps };
        }
        return {
            name: `Set ${s.set}`,
            type: "line" as const,
            showSymbol: true,
            symbolSize: 6,
            smooth: false,
            connectNulls: true,
            data,
            lineStyle: {
                color: seriesColorAt(vars, i),
                width: 2,
                ...seriesLineStyle(i),
            },
            itemStyle: { color: seriesColorAt(vars, i) },
        };
    });
}

interface TooltipParam {
    seriesName: string;
    marker: string;
    axisValue: string;
    value?: number;
    data?: ChartPoint | null;
}

/** Short, locale-stable date for the tooltip header (from the ms-epoch category). */
function formatTooltipDate(category?: string): string {
    if (!category) return "";
    const d = new Date(Number(category));
    if (Number.isNaN(d.getTime())) return category;
    return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}
