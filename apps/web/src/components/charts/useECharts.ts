/**
 * Local ECharts binding (GYM-129) — replaces the `echarts-for-react` wrapper,
 * whose value was ~40 lines of init/setOption/resize, with a tree-shakeable
 * hook over `echarts/core`. Only the pieces the progress chart actually uses
 * are registered: LineChart + grid/tooltip/legend + the canvas renderer — the
 * full echarts bundle (~1 MB) stays out of the build.
 *
 * Lifecycle: init on mount, `setOption(option, { notMerge: true, lazyUpdate:
 * true })` on every option change (the same notMerge/lazyUpdate contract the
 * old <ReactECharts> usage had), resize via a ResizeObserver on the container,
 * dispose on unmount. Re-theming stays remount-driven: the chart component
 * keys its container on themeVersion/mode, so a Telegram theme flip re-inits
 * cleanly exactly as before (spec §10.5).
 */
import { useEffect, useRef, type RefObject } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
    GridComponent,
    LegendComponent,
    TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption, EChartsType } from "echarts/core";

echarts.use([
    LineChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    CanvasRenderer,
]);

/**
 * Bind an ECharts instance to the returned container ref.
 *
 * The caller renders `<div ref={ref} />` with an explicit height (ECharts
 * cannot size against a 0-height container) and may remount it via `key` to
 * force a clean re-init (theme flips, mode switches).
 */
export function useECharts(
    option: EChartsCoreOption,
): RefObject<HTMLDivElement> {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<EChartsType | null>(null);

    // Init + dispose are tied to the container's mount lifetime.
    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;
        const chart = echarts.init(el);
        chartRef.current = chart;
        const observer = new ResizeObserver(() => chart.resize());
        observer.observe(el);
        return () => {
            observer.disconnect();
            chartRef.current = null;
            chart.dispose();
        };
    }, []);

    // Apply the option on mount and on every change. notMerge replaces the
    // whole option (no stale series linger across mode switches).
    useEffect(() => {
        chartRef.current?.setOption(option, { notMerge: true, lazyUpdate: true });
    }, [option]);

    return containerRef;
}
