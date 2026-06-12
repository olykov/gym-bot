/**
 * ECharts theming bound to the live CSS tokens (spec §10.5).
 *
 * `echartsTheme(cssVars)` reads the resolved CSS variables (so the chart follows
 * Telegram light/dark automatically — call it again on `themeChanged`) and
 * returns the shared option fragments: series colors derived from `--accent`,
 * axis/text in `--hint`/`--text` (Sora, tabular-nums), split-lines at `--hint`@10%,
 * a tooltip in `--bg`/`--text` (NOT ECharts' default white, which is invisible in
 * dark mode). Series beyond the color cap also vary dash style so multi-set is
 * distinguishable without relying on color alone.
 */
import type { Locale } from "@/i18n/locales";
import { getLocale } from "@/i18n/locale";
import { shortMonthInDate } from "@/i18n/datetime";

export interface CssVars {
    accent: string;
    hint: string;
    text: string;
    bg: string;
    hairline: string;
    fontBody: string;
}

/** Read the current resolved values of the tokens we theme the chart with. */
export function readCssVars(): CssVars {
    const root = document.documentElement;
    const s = getComputedStyle(root);
    const get = (name: string, fallback: string) =>
        s.getPropertyValue(name).trim() || fallback;
    return {
        accent: get("--accent", "#e5482f"),
        hint: get("--hint", "#8a8f99"),
        text: get("--text", "#1a1a1a"),
        bg: get("--bg", "#ffffff"),
        hairline: get("--hairline", "rgba(138,143,153,0.12)"),
        fontBody: get("--font-body", "Sora, ui-sans-serif, sans-serif"),
    };
}

/**
 * Series color ramp keyed to `--accent` (spec §10.5): the primary set is the
 * full accent; subsequent sets shift toward `--hint` so multi-set stays on-brand
 * and legible in dark mode. Color is capped — beyond it, dash style carries the
 * distinction (see {@link seriesLineStyle}).
 */
export function seriesColors(vars: CssVars): string[] {
    const { accent, hint } = vars;
    const mix = (pct: number) =>
        `color-mix(in srgb, ${accent} ${pct}%, ${hint})`;
    return [accent, mix(70), mix(45), mix(25)];
}

/** Solid for the first colors, then cycle dashes so >~4 sets stay distinct. */
export function seriesLineStyle(index: number): { type: "solid" | "dashed" | "dotted" } {
    const colorCap = 4;
    if (index < colorCap) return { type: "solid" };
    const dashes: Array<"dashed" | "dotted"> = ["dashed", "dotted"];
    return { type: dashes[(index - colorCap) % dashes.length] };
}

/** Color for a given series index (wraps within the capped ramp). */
export function seriesColorAt(vars: CssVars, index: number): string {
    const colors = seriesColors(vars);
    return colors[index % colors.length];
}

/**
 * Compact, single-tier x-axis label: `DD MMM` (e.g. `02 Jun` / ru `02 июн`,
 * Intl-based — GYM-109). One legible label per tick avoids ECharts' default
 * month/year-over-day two-tier labels overlapping the day numbers in a 360px
 * column (GYM-53 §10.5).
 */
export function formatAxisDate(
    value: number,
    locale: Locale = getLocale(),
): string {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "";
    const day = String(d.getDate()).padStart(2, "0");
    return `${day} ${shortMonthInDate(d, locale)}`;
}

/** Target number of x-axis labels — keeps the axis legible at 360px (GYM-57 §10.5). */
const MAX_AXIS_LABELS = 5;

/**
 * Indices to label on a category x-axis so the axis never crowds at 360px
 * regardless of point count (GYM-57 §2a). For `count` categories return the set
 * of indices to label: up to {@link MAX_AXIS_LABELS} evenly-spaced positions
 * (always first + last). The full date still rides in the tooltip.
 */
export function sparseLabelIndices(count: number): Set<number> {
    const keep = new Set<number>();
    if (count <= 0) return keep;
    if (count <= MAX_AXIS_LABELS) {
        for (let i = 0; i < count; i++) keep.add(i);
        return keep;
    }
    const step = (count - 1) / (MAX_AXIS_LABELS - 1);
    for (let i = 0; i < MAX_AXIS_LABELS; i++) {
        keep.add(Math.round(i * step));
    }
    return keep;
}

/** Shared, token-bound base option (axes, grid, tooltip, legend, text style). */
export function baseChartOption(vars: CssVars) {
    const axisText = {
        color: vars.hint,
        fontFamily: vars.fontBody,
        fontSize: 11,
    };
    return {
        textStyle: { fontFamily: vars.fontBody, color: vars.text },
        grid: { left: 8, right: 12, top: 28, bottom: 8, containLabel: true },
        legend: {
            type: "scroll" as const,
            top: 0,
            icon: "roundRect",
            itemWidth: 14,
            itemHeight: 8,
            textStyle: {
                color: vars.text,
                fontFamily: vars.fontBody,
                fontSize: 11,
            },
        },
        tooltip: {
            trigger: "axis" as const,
            // GYM-123 #9: explicit so a plain TAP shows values on coarse
            // pointers (touch maps taps to click) — never rely on the
            // version-dependent ECharts default.
            triggerOn: "mousemove|click" as const,
            backgroundColor: vars.bg,
            borderColor: vars.hairline,
            borderWidth: 1,
            textStyle: {
                color: vars.text,
                fontFamily: vars.fontBody,
                fontSize: 12,
            },
            extraCssText: "font-variant-numeric: tabular-nums;",
        },
        xAxis: {
            // Category axis over the distinct session dates: the chart supplies
            // `data` + a thinning `axisLabel.interval` so only a few sparse
            // `DD MMM` labels render at 360px (GYM-57 §2a). The full date rides
            // in the tooltip. Equal-spaced points read cleanly as a progression.
            type: "category" as const,
            boundaryGap: false,
            axisLine: { lineStyle: { color: vars.hint } },
            axisLabel: {
                ...axisText,
                // `data` holds ms-epoch strings; render the compact `DD MMM`.
                // The chart sets `interval` to keep only sparse labels.
                formatter: (value: string) => formatAxisDate(Number(value)),
                margin: 10,
            },
            axisTick: { show: false },
            splitLine: { show: false },
        },
        yAxis: {
            type: "value" as const,
            axisLine: { show: false },
            axisLabel: axisText,
            splitLine: {
                lineStyle: { color: vars.hairline, type: "dashed" as const },
            },
        },
    };
}
