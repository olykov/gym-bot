/**
 * Exercise progress chart (spec §10.3, GYM-57) — ECharts (via the local
 * {@link useECharts} binding, GYM-129), weight over time on a shared category
 * axis of the distinct session dates. Three modes:
 *
 *  - **By Weight** (default): ONE line = the max weight logged per session/date —
 *    the strength-over-time trend ("how my bench grew"), derived client-side from
 *    the per-set series (no API change). Each point carries the reps of that day's
 *    heaviest set so the tooltip reads `{weight}kg × {reps}` (GYM-63).
 *  - **By Set**: one line per set number (the original behavior). Reps ride along
 *    in each tooltip row so the chart stays legible at 360px without a second axis.
 *  - **e1RM** (GYM-133, doc 03 §4.1): ONE line = the max Epley e1RM per
 *    session/date, derived client-side exactly like By Weight (no API change;
 *    math in src/lib/e1rm.ts). The tooltip names the source set:
 *    `e1RM: {v}kg ({w} × {r})`.
 *
 * The tooltip shows the full date plus `{weight}kg × {reps}` rows in the weight/
 * set modes; reps (and, for e1RM, the source weight) ride in each point's data
 * (spec §10.5 token theming unchanged).
 *
 * X-axis labels are thinned to ~5 sparse `DD MMM` ticks (GYM-57 §2a); the full
 * date stays in the tooltip. Theming is bound to tokens (spec §10.5) via
 * {@link echartsTheme}: series take the `--accent`→`--hint` ramp, axes/text use
 * `--hint`/`--text` in Sora tabular-nums, the tooltip is `--bg`/`--text`, and
 * beyond the color cap series vary dash style so multi-set is distinguishable
 * without relying on color alone. It re-themes on Telegram `themeChanged`.
 */
import { useMemo } from "react";
import type { EChartsCoreOption } from "echarts/core";
import { useECharts } from "@/components/charts/useECharts";
import type { Locale } from "@/i18n/locales";
import { useT, type Translator } from "@/i18n/catalog";
import { Card } from "@/components/ui/Card";
import { useThemeVersion } from "@/hooks/useThemeVersion";
import type { ExerciseProgress } from "@/api/analytics";
import { maxE1rmByDate } from "@/lib/e1rm";
import {
    baseChartOption,
    formatAxisDate,
    readCssVars,
    seriesColorAt,
    seriesLineStyle,
    sparseLabelIndices,
} from "@/components/charts/echartsTheme";

export type ProgressMode = "weight" | "set" | "e1rm";

interface ExerciseProgressChartProps {
    title: string;
    progress: ExerciseProgress;
    /**
     * "weight" = single max-weight-per-date trend; "set" = one line per set;
     * "e1rm" = single max-Epley-e1RM-per-date trend (GYM-133).
     */
    mode: ProgressMode;
}

export function ExerciseProgressChart({
    title,
    progress,
    mode,
}: ExerciseProgressChartProps) {
    const translator = useT();
    const { t, locale } = translator;
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
            mode === "set"
                ? bySetSeries(progress, indexOf, vars, translator)
                : mode === "e1rm"
                  ? [byE1rmSeries(progress, dates, vars, translator)]
                  : [byWeightSeries(progress, dates, vars, translator)];

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
                mode === "set" ? base.legend : { ...base.legend, show: false },
            tooltip: {
                ...base.tooltip,
                // Full date header + per-line rows. Weight/set modes render
                // `{weight}kg × {reps}` (spec §11.2 figure format) — reps ride
                // in each point's `data.reps` (By Weight: the reps of that
                // date's heaviest set, see {@link byWeightSeries}). e1RM mode
                // (GYM-133) names the SOURCE set instead:
                // `e1RM: {v}kg ({w} × {r})` — w×r ride in the point's data.
                formatter: (params: TooltipParam[]) => {
                    if (!params.length) return "";
                    const date = formatTooltipDate(params[0].axisValue, locale);
                    const kg = t("unit.kg");
                    const rows = params
                        .map((p) => {
                            const reps = p.data?.reps;
                            if (mode === "e1rm") {
                                const weight = p.data?.weight;
                                const source =
                                    weight != null && reps != null
                                        ? ` (${weight} × ${reps})`
                                        : "";
                                return `${p.marker}${p.seriesName}: ${p.value}${kg}${source}`;
                            }
                            return `${p.marker}${p.seriesName}: ${p.value}${kg}${
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
            {/* GYM-77 #2: truncate long exercise names in the chart title.
                Full name available on hover via title attr. */}
            <div className="mb-3 truncate font-display text-title text-text" title={title}>{title}</div>
            <ChartCanvas
                // Key on theme + mode so ECharts re-inits cleanly on a flip/switch.
                key={`${themeVersion}-${mode}`}
                option={option}
            />
        </Card>
    );
}

/**
 * The chart container: binds {@link useECharts} to a fixed-height div. Kept as
 * its own component so the parent's `key` remounts it — init/dispose re-run and
 * the chart re-reads the theme tokens, exactly like the old wrapper's re-init.
 */
function ChartCanvas({ option }: { option: EChartsCoreOption }) {
    const chartRef = useECharts(option);
    return <div ref={chartRef} style={{ height: 256, width: "100%" }} />;
}

/**
 * A category point carrying its reps (and, in e1RM mode, the source set's
 * weight) for the tooltip. `null` in the data array = no value on that date.
 */
interface ChartPoint {
    value: number;
    reps?: number;
    /** e1RM mode only: the weight of the set that produced the max e1RM. */
    weight?: number;
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
    { t }: Translator,
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
        name: t("chart.maxWeight"),
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

/**
 * e1RM (GYM-133): one line = the MAX Epley e1RM per session/date, mirroring
 * {@link byWeightSeries}'s client-side derivation (math + tie rule live in
 * {@link maxE1rmByDate}, unit-tested in src/lib/e1rm.test.ts). Each point
 * carries the SOURCE set's weight×reps so the tooltip reads
 * `e1RM: {v}kg ({w} × {r})`. Values are display-rounded to 1 decimal.
 */
function byE1rmSeries(
    progress: ExerciseProgress,
    dates: number[],
    vars: ReturnType<typeof readCssVars>,
    { t }: Translator,
) {
    const bestByDate = maxE1rmByDate(progress);
    const data: Array<ChartPoint | null> = dates.map((ms) => {
        const top = bestByDate.get(ms);
        return top == null
            ? null
            : { value: top.e1rm, weight: top.weight, reps: top.reps };
    });
    return {
        name: t("chart.e1rm"),
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
    { t }: Translator,
) {
    return progress.series.map((s, i) => {
        const data: Array<ChartPoint | null> = new Array(indexOf.size).fill(null);
        for (const p of s.points) {
            const ms = new Date(p.date).getTime();
            const idx = indexOf.get(ms);
            if (idx != null) data[idx] = { value: p.weight, reps: p.reps };
        }
        return {
            name: t("set.n", { n: s.set }),
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

/** Short, locale-aware date for the tooltip header (from the ms-epoch category). */
function formatTooltipDate(category: string | undefined, locale: Locale): string {
    if (!category) return "";
    const d = new Date(Number(category));
    if (Number.isNaN(d.getTime())) return category;
    return d.toLocaleDateString(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}
