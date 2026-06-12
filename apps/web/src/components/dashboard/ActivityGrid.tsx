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
 *
 * GYM-117 (tap-to-inspect): `title` tooltips never show on touch, so tapping a
 * non-padding cell selects it (a gapped double accent ring — distinguishable
 * from the solid 2px "today" ring, ring-only so reduced motion needs no gate)
 * and a detail line under the grid shows `N sets · MON 02 JUN`. Days WITH sets
 * make the line a ≥44px chevron button into `/history/:date` (drill-in
 * transition). The detail row's height is ALWAYS reserved (it shows a quiet
 * "Tap a day" hint while nothing is selected) so selecting never shifts the
 * card layout. Tapping the same cell, or anywhere else in the grid, deselects.
 *
 * GYM-123 #2: a tiny Sora --hint month-labels row sits above the columns
 * (same size idiom as the weekday rail); labels come from the pure
 * monthLabels() helper (month transitions, overlap-guarded).
 */
import { useMemo, useState } from "react";
import { useT } from "@/i18n/catalog";
import { Card } from "@/components/ui/Card";
import { Divider } from "@/components/ui/Divider";
import { hapticImpact } from "@/telegram/webapp";
import { useTransitionNavigate } from "@/components/shell/useTransitionNavigate";
import type { ActivityDay } from "@/api/analytics";
import {
    buildGrid,
    cellDetailText,
    cellTooltip,
    monthLabels,
    weekdayRail,
    type GridCell,
} from "./activityGridModel";

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
    const { t, locale } = useT();
    // Build once per data change; today is read at render (fine for a daily grid).
    const columns = useMemo(() => buildGrid(days), [days]);
    // GYM-123 #2: month label per column (null = unlabelled), pure helper.
    const labels = useMemo(() => monthLabels(columns, locale), [columns, locale]);
    // Localized Monday-first weekday rail (GYM-109).
    const weekdays = useMemo(() => weekdayRail(locale), [locale]);
    const transitionNavigate = useTransitionNavigate();

    // GYM-117: selection is keyed by DATE (not the cell object) so a refetch
    // rebuilds the grid without orphaning the selection's sets count.
    const [selectedDate, setSelectedDate] = useState<string | null>(null);
    const selected = useMemo(() => {
        if (!selectedDate) return null;
        for (const week of columns) {
            const hit = week.find((c) => c.date === selectedDate);
            if (hit) return hit;
        }
        return null;
    }, [columns, selectedDate]);

    function toggleCell(cell: GridCell): void {
        if (!cell.date) return; // padding cells are inert
        if (cell.date === selectedDate) {
            setSelectedDate(null);
            return;
        }
        hapticImpact("light");
        setSelectedDate(cell.date);
    }

    function openSelectedDay(): void {
        if (!selected?.date || selected.sets === 0) return;
        hapticImpact("light");
        transitionNavigate(`/history/${selected.date}`, "forward");
    }

    return (
        <Card>
            <div className="flex items-baseline justify-between">
                <h2 className="font-display text-title text-text">
                    {t("activity.title")}
                </h2>
                <span className="text-label uppercase tracking-wide text-hint">
                    {t("activity.window")}
                </span>
            </div>

            <Divider className="my-3" />

            {/* Tapping the grid OUTSIDE a cell (rail, gaps) deselects. */}
            <div className="flex gap-1" onClick={() => setSelectedDate(null)}>
                {/* Weekday rail (Sora, --hint), aligned to the 7 rows. The
                    spacer on top mirrors the month-label row's height so the
                    rail labels stay level with the grid rows (GYM-123 #2). */}
                <div className="flex flex-col pr-1">
                    <span className="mb-1 h-3 shrink-0" aria-hidden />
                    <div className="flex flex-1 flex-col justify-between py-[1px]">
                        {weekdays.map((d, i) => (
                            <span
                                key={i}
                                className="text-micro text-hint"
                            >
                                {d}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="flex min-w-0 flex-1 flex-col">
                    {/* GYM-123 #2: month labels row — one flex-1 slot per column
                        (same gap as the grid, so slots align with columns 1:1).
                        Labels render nowrap and spill right over the following
                        unlabelled slots; the model's min-gap rule guarantees no
                        two labels are close enough to collide at 26 columns.
                        Decorative (dates already live in each cell's label). */}
                    <div className="mb-1 flex h-3 gap-1" aria-hidden>
                        {labels.map((label, i) => (
                            <span key={i} className="relative min-w-0 flex-1">
                                {label ? (
                                    <span
                                        className="absolute left-0 top-0 whitespace-nowrap text-micro text-hint"
                                    >
                                        {label}
                                    </span>
                                ) : null}
                            </span>
                        ))}
                    </div>

                    {/* Flex-fill columns: each divides the remaining width => no scroll. */}
                    <div className="flex gap-1">
                        {columns.map((week, col) => (
                            <div key={col} className="flex flex-1 flex-col gap-1">
                                {week.map((cell, row) => (
                                    <Cell
                                        key={row}
                                        cell={cell}
                                        delayStep={col + row}
                                        selected={
                                            cell.date !== null &&
                                            cell.date === selectedDate
                                        }
                                        onToggle={toggleCell}
                                    />
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <DetailLine cell={selected} onOpen={openSelectedDay} />

            <Legend />
        </Card>
    );
}

/**
 * A single day square. Today gets a solid 2px --accent ring; the SELECTED cell
 * gets a gapped (--bg spacer) double ring so both states stay distinguishable
 * even when they coincide. Padding cells stay inert empty divs; real days are
 * buttons (tap-to-inspect, GYM-117) — `title` kept for desktop hover.
 */
function Cell({
    cell,
    delayStep,
    selected,
    onToggle,
}: {
    cell: GridCell;
    delayStep: number;
    selected: boolean;
    onToggle: (cell: GridCell) => void;
}) {
    const isEmpty = cell.level === 0;
    const background = isEmpty
        ? "var(--grid-empty-bg)"
        : LEVEL_VAR[cell.level as 1 | 2 | 3 | 4];

    // Selected ring wins (thicker, gapped); today keeps its solid 2px ring.
    const ring = selected
        ? "0 0 0 2px var(--bg), 0 0 0 4px var(--accent)"
        : cell.isToday
          ? "0 0 0 2px var(--accent)"
          : undefined;

    const style = {
        background,
        border: isEmpty
            ? "1px solid var(--grid-empty-border)"
            : "1px solid transparent",
        // Today/selected rings (graphical accent use is a11y-OK at any size).
        boxShadow: ring,
        // Lift the selected ring above neighbouring cells' gaps.
        zIndex: selected ? 1 : undefined,
        // Stagger the first-paint ink-in (CSS gates reduced motion).
        ["--cell-delay" as string]: `${delayStep * 6}ms`,
    };

    // Padding cell (future day): not tappable, hidden from a11y.
    if (cell.date === null) {
        return (
            <div
                className="grid-cell aspect-square w-full rounded-sm"
                style={style}
                aria-hidden
            />
        );
    }

    return (
        <button
            type="button"
            className="grid-cell relative aspect-square w-full rounded-sm"
            title={cellTooltip(cell)}
            aria-label={cellTooltip(cell)}
            aria-pressed={selected}
            style={style}
            onClick={(e) => {
                e.stopPropagation(); // keep the grid-level deselect out
                onToggle(cell);
            }}
        />
    );
}

/**
 * The reserved inspect row under the grid (GYM-117). Height is reserved in
 * EVERY state (hint → plain text → button) so selection never shifts the card.
 * Days with sets render a ≥44px chevron button into `/history/:date`; empty
 * days render plain text (no navigation affordance).
 */
function DetailLine({
    cell,
    onOpen,
}: {
    cell: GridCell | null;
    onOpen: () => void;
}) {
    const { t } = useT();
    const text = cell ? cellDetailText(cell) : null;

    return (
        <div className="mt-2 flex min-h-[44px] items-center justify-center">
            {text === null ? (
                <span className="text-label text-hint">
                    {t("activity.tapADay")}
                </span>
            ) : cell && cell.sets > 0 ? (
                <button
                    type="button"
                    onClick={onOpen}
                    className="press-95 tabular flex min-h-[44px] items-center gap-2 rounded-md px-4 text-base text-text"
                >
                    {text}
                    {/* Drill-in affordance (mirrors DayCard's chevron). */}
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        aria-hidden
                        className="shrink-0"
                    >
                        <path
                            d="M9 6l6 6-6 6"
                            stroke="var(--hint)"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                </button>
            ) : (
                <span className="tabular text-base text-text">{text}</span>
            )}
        </div>
    );
}

/** Less → More ramp legend (Sora), mirrors the cell ramp. */
function Legend() {
    const { t } = useT();
    const swatches: Array<{ bg: string; border?: string }> = [
        { bg: "var(--grid-empty-bg)", border: "var(--grid-empty-border)" },
        { bg: "var(--grid-l1)" },
        { bg: "var(--grid-l2)" },
        { bg: "var(--grid-l3)" },
        { bg: "var(--grid-l4)" },
    ];
    return (
        <div className="mt-3 flex items-center justify-end gap-1">
            <span className="text-label text-hint">{t("activity.less")}</span>
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
            <span className="text-label text-hint">{t("activity.more")}</span>
        </div>
    );
}
