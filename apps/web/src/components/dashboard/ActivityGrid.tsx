/**
 * GitHub-style activity grid (spec §10.2) — Monday-first, chalk→iron accent ramp
 * (NOT GitHub green), "today" ring, per-cell tooltip "N sets on <date>".
 *
 * 360px fit (acceptance criterion): the grid is laid out with CSS flex-fill, not
 * fixed-px cells — 26 columns each `flex:1` with `aspect-ratio:1`, separated by
 * the 4px gap token. Columns therefore divide whatever width the card gives them,
 * so the 26-week window ALWAYS fits the container with no horizontal scroll, at
 * 360px and on any narrower phone. (Full-year, which would need the one
 * sanctioned in-card scroll, is deferred.)
 *
 * The ramp + empty-cell colors come from tokens.css (light + dark, with the dark
 * empty cell brightened to stay visible). On first paint cells "ink-in" with a
 * staggered fade, gated by prefers-reduced-motion via the CSS class.
 */
import { useMemo } from "react";
import { Card } from "@/components/ui/Card";
import { Divider } from "@/components/ui/Divider";
import type { ActivityDay } from "@/api/analytics";
import {
    buildGrid,
    cellTooltip,
    type GridCell,
} from "./activityGridModel";

/** Monday-first weekday rails; only odd rows get a visible label (space). */
const WEEKDAYS = ["Mon", "", "Wed", "", "Fri", "", "Sun"];

/** Map a level bucket to its ramp token (empty handled separately). */
const LEVEL_VAR: Record<1 | 2 | 3 | 4, string> = {
    1: "var(--grid-l1)",
    2: "var(--grid-l2)",
    3: "var(--grid-l3)",
    4: "var(--grid-l4)",
};

interface ActivityGridProps {
    days: ActivityDay[];
}

export function ActivityGrid({ days }: ActivityGridProps) {
    // Build once per data change; today is read at render (fine for a daily grid).
    const columns = useMemo(() => buildGrid(days), [days]);

    return (
        <Card>
            <div className="flex items-baseline justify-between">
                <h2 className="font-display text-title text-text">Activity</h2>
                <span className="text-label uppercase tracking-wide text-hint">
                    Last 26 weeks
                </span>
            </div>

            <Divider className="my-3" />

            <div className="flex gap-1">
                {/* Weekday rail (Sora, --hint), aligned to the 7 rows. */}
                <div className="flex flex-col justify-between py-[1px] pr-1">
                    {WEEKDAYS.map((d, i) => (
                        <span
                            key={i}
                            className="text-label leading-none text-hint"
                            style={{ fontSize: "0.625rem" }}
                        >
                            {d}
                        </span>
                    ))}
                </div>

                {/* Flex-fill columns: each divides the remaining width => no scroll. */}
                <div className="flex min-w-0 flex-1 gap-1">
                    {columns.map((week, col) => (
                        <div key={col} className="flex flex-1 flex-col gap-1">
                            {week.map((cell, row) => (
                                <Cell
                                    key={row}
                                    cell={cell}
                                    delayStep={col + row}
                                />
                            ))}
                        </div>
                    ))}
                </div>
            </div>

            <Legend />
        </Card>
    );
}

/** A single day square. Today gets an --accent ring; padding cells stay empty. */
function Cell({ cell, delayStep }: { cell: GridCell; delayStep: number }) {
    const isEmpty = cell.level === 0;
    const background = isEmpty
        ? "var(--grid-empty-bg)"
        : LEVEL_VAR[cell.level as 1 | 2 | 3 | 4];

    return (
        <div
            className="grid-cell aspect-square w-full rounded-sm"
            title={cellTooltip(cell)}
            style={{
                background,
                border: isEmpty
                    ? "1px solid var(--grid-empty-border)"
                    : "1px solid transparent",
                // Today ring (graphical accent use is a11y-OK at any size).
                boxShadow: cell.isToday
                    ? "0 0 0 2px var(--accent)"
                    : undefined,
                // Stagger the first-paint ink-in (CSS gates reduced motion).
                ["--cell-delay" as string]: `${delayStep * 6}ms`,
            }}
            aria-hidden={cell.date === null}
        />
    );
}

/** Less → More ramp legend (Sora), mirrors the cell ramp. */
function Legend() {
    const swatches: Array<{ bg: string; border?: string }> = [
        { bg: "var(--grid-empty-bg)", border: "var(--grid-empty-border)" },
        { bg: "var(--grid-l1)" },
        { bg: "var(--grid-l2)" },
        { bg: "var(--grid-l3)" },
        { bg: "var(--grid-l4)" },
    ];
    return (
        <div className="mt-3 flex items-center justify-end gap-1">
            <span className="text-label text-hint">Less</span>
            {swatches.map((s, i) => (
                <span
                    key={i}
                    className="h-2 w-2 rounded-sm"
                    style={{
                        background: s.bg,
                        border: s.border ? `1px solid ${s.border}` : undefined,
                    }}
                />
            ))}
            <span className="text-label text-hint">More</span>
        </div>
    );
}
