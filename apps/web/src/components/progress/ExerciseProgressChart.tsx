/**
 * Exercise progress chart (spec §10.3) — `echarts-for-react`, one line series per
 * set number, weight over time. Reps ride along in each tooltip row so the chart
 * stays legible at 360px without a second axis crowding the frame.
 *
 * Theming is bound to tokens (spec §10.5) via {@link echartsTheme}: series take
 * the `--accent`→`--hint` ramp, axes/text use `--hint`/`--text` in Sora tabular-
 * nums, the tooltip is `--bg`/`--text` (not ECharts' default white), and beyond
 * the color cap series vary dash style so multi-set is distinguishable without
 * relying on color alone. It re-themes on Telegram `themeChanged` (the option is
 * rebuilt when the theme-version bumps), and resizes to the container.
 */
import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { Card } from "@/components/ui/Card";
import { useThemeVersion } from "@/hooks/useThemeVersion";
import type { ExerciseProgress } from "@/api/analytics";
import {
    baseChartOption,
    readCssVars,
    seriesColorAt,
    seriesLineStyle,
} from "@/components/charts/echartsTheme";

interface ExerciseProgressChartProps {
    title: string;
    progress: ExerciseProgress;
}

export function ExerciseProgressChart({
    title,
    progress,
}: ExerciseProgressChartProps) {
    // Re-read tokens + rebuild the option whenever Telegram flips light/dark.
    const themeVersion = useThemeVersion();

    const option = useMemo(() => {
        const vars = readCssVars();
        const base = baseChartOption(vars);

        const series = progress.series.map((s, i) => ({
            name: `Set ${s.set}`,
            type: "line" as const,
            showSymbol: true,
            symbolSize: 6,
            smooth: false,
            // weight is the plotted value; reps travel in the data point for the
            // tooltip (encode pins the y dimension to weight).
            data: s.points.map((p) => ({
                value: [p.date, p.weight],
                reps: p.reps,
            })),
            lineStyle: {
                color: seriesColorAt(vars, i),
                width: 2,
                ...seriesLineStyle(i),
            },
            itemStyle: { color: seriesColorAt(vars, i) },
        }));

        return {
            ...base,
            tooltip: {
                ...base.tooltip,
                // Per-set weight + reps; tabular-nums keeps the rows aligned.
                formatter: (params: TooltipParam[]) => {
                    if (!params.length) return "";
                    const date = formatDate(params[0].value?.[0]);
                    const rows = params
                        .map((p) => {
                            const weight = p.value?.[1];
                            const reps = p.data?.reps;
                            return `${p.marker}${p.seriesName}: ${weight} kg${
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
    }, [progress, themeVersion]);

    return (
        <Card>
            <div className="mb-3 font-display text-title text-text">{title}</div>
            <ReactECharts
                // Key on theme so ECharts re-inits cleanly when the palette flips.
                key={themeVersion}
                option={option}
                notMerge
                lazyUpdate
                style={{ height: 256, width: "100%" }}
                opts={{ renderer: "svg" }}
            />
        </Card>
    );
}

interface TooltipParam {
    seriesName: string;
    marker: string;
    value?: [string, number];
    data?: { reps?: number };
}

/** Short, locale-stable date for the tooltip header. */
function formatDate(iso?: string): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}
