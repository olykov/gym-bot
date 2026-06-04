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
            type: "time" as const,
            axisLine: { lineStyle: { color: vars.hint } },
            axisLabel: axisText,
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
