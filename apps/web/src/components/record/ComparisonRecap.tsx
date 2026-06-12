/**
 * GYM-130 — the recap rows of the SetLogger (presentational, spec §12.3).
 *
 * Two modes, decided by the controller via `hasGhost`:
 *  - **Comparison** (a prior session exists): a two-column TODAY | LAST TIME
 *    table matched by set number, ASC (Set 1 top). Ghost rows (last-time
 *    only) render the LAST TIME figure in --hint at ~70% opacity with a
 *    quiet placeholder in the today column — the standing target. Saved
 *    rows that match a ghost get a per-set delta: weight first, reps
 *    tiebreak (operator decision, LOCKED — see computeDelta in derive.ts).
 *    Up → accent `▲ +2.5kg`; equal → hint `=`; down → hint `▼ −2.5kg`
 *    (quiet, never punitive red). ▲/▼ are unicode geometric figures.
 *  - **Single column** (no prior session at all): exactly the pre-GYM-130
 *    recap — no ghost column, no headers, no empty noise.
 *
 * Pure props + markup; the scroll container, refs map and auto-scroll
 * effects live in SetLogger (the container). Rows register their elements
 * via `registerRow` so the container can scrollIntoView by set number.
 */
import { useT } from "@/i18n/catalog";
import { SetFigure } from "@/components/ui/SetFigure";
import type { ComparisonRow, Delta } from "./derive";

/**
 * Shared 4-track template — set | today | delta | last — so the header and
 * every row align. Sized to keep each row ONE line at 360px (tight gap,
 * fixed set/delta tracks, figures share the rest; whitespace-nowrap on the
 * row stops figures from wrapping at their internal spaces).
 */
const GRID =
    "grid grid-cols-[2.5rem_minmax(0,1fr)_3.75rem_minmax(0,1fr)] items-center gap-x-1";

interface ComparisonRecapProps {
    /** ASC comparison rows from buildComparisonRows (derive.ts). */
    rows: ComparisonRow[];
    /** Prior session exists → comparison mode; else single-column mode. */
    hasGhost: boolean;
    /** Set number whose row flares on a PR-beat (GYM-104), or null. */
    flareSet: number | null;
    /**
     * GYM-131: the set saved THIS session most recently (null before the
     * first save / after reopen). Its row mounts with the entrance
     * choreography — fade + rise + soft flash — and its delta badge slides
     * in after the row lands. The classes stay on the element (CSS runs
     * once on mount); the next save moves them to the new row.
     */
    justSavedSet: number | null;
    /** Element registrar keyed by set number — the auto-scroll targets. */
    registerRow: (set: number, el: HTMLDivElement | null) => void;
}

/**
 * GYM-131 row animation classes: every just-saved row enters (rise + soft
 * flash); a PR-beat row keeps the rise but upgrades the flash to the
 * stronger pr-flare (combined rule in index.css). Both are disabled under
 * prefers-reduced-motion by the index.css media block.
 */
function rowAnimClass(
    set: number,
    justSavedSet: number | null,
    flareSet: number | null,
): string {
    const enter = justSavedSet === set ? " row-enter" : "";
    const flare = flareSet === set ? " pr-flare" : "";
    return `${enter}${flare}`;
}

/** The per-set delta figure: accent up / hint `=` / hint down (tabular). */
function DeltaFigure({ delta }: { delta: Delta }) {
    const { t, tp } = useT();
    if (delta.kind === "eq") {
        return <span className="tabular text-label text-hint">=</span>;
    }
    if (delta.metric === "weight") {
        return (
            <span
                className={`tabular text-label ${
                    delta.kind === "up"
                        ? "font-semibold text-accent"
                        : "text-hint"
                }`}
            >
                {t(
                    delta.kind === "up" ? "delta.upWeight" : "delta.downWeight",
                    { amount: delta.amount },
                )}
            </span>
        );
    }
    return (
        <span
            className={`tabular text-label ${
                delta.kind === "up" ? "font-semibold text-accent" : "text-hint"
            }`}
        >
            {tp(
                delta.kind === "up" ? "delta.upReps" : "delta.downReps",
                delta.amount,
            )}
        </span>
    );
}

export function ComparisonRecap({
    rows,
    hasGhost,
    flareSet,
    justSavedSet,
    registerRow,
}: ComparisonRecapProps) {
    const { t } = useT();

    // No prior session → exactly the pre-GYM-130 single-column recap.
    if (!hasGhost) {
        return (
            <div className="mt-2 flex flex-col divide-y divide-hairline">
                {rows.map((row) =>
                    row.today ? (
                        <div
                            key={row.set}
                            ref={(el) => registerRow(row.set, el)}
                            className={`flex min-h-[36px] items-center justify-between gap-4${rowAnimClass(
                                row.set,
                                justSavedSet,
                                flareSet,
                            )}`}
                        >
                            <span className="text-label uppercase tracking-wide text-hint">
                                {t("set.n", { n: row.set })}
                            </span>
                            <SetFigure
                                weight={row.today.weight}
                                reps={row.today.reps}
                            />
                        </div>
                    ) : null,
                )}
            </div>
        );
    }

    return (
        <>
            {/* Column headers — tiny uppercase hint labels (TODAY | LAST TIME). */}
            <div
                className={`${GRID} text-label uppercase tracking-wide text-hint`}
            >
                <span />
                <span>{t("recap.today")}</span>
                <span />
                <span className="text-right">{t("recap.lastTime")}</span>
            </div>
            <div className="mt-2 flex flex-col divide-y divide-hairline">
                {rows.map((row) => (
                    <div
                        key={row.set}
                        ref={(el) => registerRow(row.set, el)}
                        className={`${GRID} min-h-[36px] whitespace-nowrap${rowAnimClass(
                            row.set,
                            justSavedSet,
                            flareSet,
                        )}`}
                    >
                        <span className="text-label uppercase tracking-wide text-hint">
                            {t("set.n", { n: row.set })}
                        </span>
                        {row.today ? (
                            // Priority session > server > ✓-only is already
                            // resolved in the row model; null w×r renders the
                            // honest `— · —` figure (GYM-123 #3).
                            <SetFigure
                                weight={row.today.weight}
                                reps={row.today.reps}
                            />
                        ) : (
                            // Ghost row: quiet placeholder — not `— · —`,
                            // which means "logged, numbers unknown".
                            <span
                                aria-hidden="true"
                                className="tabular font-display text-title leading-none text-hint opacity-50"
                            >
                                —
                            </span>
                        )}
                        {row.delta ? (
                            // GYM-131 #2: on the just-saved row the badge
                            // slides in after the row lands (CSS delay).
                            <span
                                className={
                                    justSavedSet === row.set
                                        ? "delta-enter"
                                        : undefined
                                }
                            >
                                <DeltaFigure delta={row.delta} />
                            </span>
                        ) : (
                            <span />
                        )}
                        <span className="justify-self-end">
                            {row.last ? (
                                <SetFigure
                                    ghost
                                    weight={row.last.weight}
                                    reps={row.last.reps}
                                />
                            ) : null}
                        </span>
                    </div>
                ))}
            </div>
        </>
    );
}
