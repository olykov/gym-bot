/**
 * The one set row (spec §11.3 / §11.5) — extends the <ListRow> idea, reused for
 * every set in the day detail. Leading `Set {n}` (Sora --hint), trailing
 * `{weight}kg × {reps}` (Bebas-leaning, tabular-nums so rows align). ≥44px tall.
 *
 * GYM-153: when `set.is_pr` is true, the PR marker moves to the ROW MIDDLE (the
 * free space between the `Set N` label and the figure). The figure cluster at the
 * trailing edge is now just the numbers — no chip — so the right-aligned x of the
 * figure is IDENTICAL on PR and non-PR rows (no shift). The marker labels from
 * `set.pr_kind`: "weight" → "Weight PR", "reps" → "Reps PR". On narrow rows the
 * label collapses to just "PR" via a CSS container-query on the row element.
 *
 * The chip still gets the GYM-141 accent-pulse on appear (spec §9.4), behind
 * prefers-reduced-motion. Non-PR rows are layout-identical (empty flex-1 middle).
 *
 * DayCard day-level badge (GYM-136) uses `has_pr` with no `pr_kind` and renders
 * its own <StatChip>{t("pr")}</StatChip> unchanged — this change does NOT touch
 * that component or the shared <StatChip>.
 *
 * Interactions:
 *  - tap the row → opens the editor (`onEdit`) with a light impact haptic;
 *  - swipe-left → reveals a single --accent Delete action (`onDelete`). Swipe
 *    only REVEALS — the destructive action still routes through the two-step
 *    in-sheet confirm (§11.4 / §11.7), so a stray swipe never deletes.
 *
 * The swipe is a pure transform (gated by prefers-reduced-motion via the track's
 * transition class). `training_id` is carried by the caller as the mutation key.
 */
import { useRef, useState } from "react";
import { useT } from "@/i18n/catalog";
import { hapticImpact } from "@/telegram/webapp";
import type { TrainingSet } from "@/api/training";
import { SetFigure } from "./SetFigure";
import { StatChip } from "./StatCard";
import { prLabelKeys } from "./prLabel";

interface SetRowProps {
    set: TrainingSet;
    onEdit: () => void;
    onDelete: () => void;
}

/** Px the row slides left to expose the delete action. */
const REVEAL = 88;
/** Drag past this commits the row to the open/closed snap. */
const THRESHOLD = REVEAL / 2;

export function SetRow({ set, onEdit, onDelete }: SetRowProps) {
    const { t } = useT();
    const [open, setOpen] = useState(false);
    const [dragX, setDragX] = useState<number | null>(null);
    const startX = useRef(0);
    const moved = useRef(false);

    const offset = dragX ?? (open ? -REVEAL : 0);

    function onPointerDown(e: React.PointerEvent): void {
        startX.current = e.clientX;
        moved.current = false;
        setDragX(open ? -REVEAL : 0);
        // GYM-125 #3: capture the pointer so a finger that leaves the row keeps
        // streaming move/up events here — without it the swipe strands half-open.
        // Guarded: older WebViews may lack setPointerCapture or throw on it.
        try {
            if (typeof e.currentTarget.setPointerCapture === "function") {
                e.currentTarget.setPointerCapture(e.pointerId);
            }
        } catch {
            /* degrade gracefully — swipe still works while inside the row */
        }
    }
    function onPointerMove(e: React.PointerEvent): void {
        if (dragX === null) return;
        const dx = e.clientX - startX.current + (open ? -REVEAL : 0);
        if (Math.abs(e.clientX - startX.current) > 6) moved.current = true;
        // Clamp: only allow swiping left to reveal, snap-back on the right.
        setDragX(Math.max(-REVEAL, Math.min(0, dx)));
    }
    function onPointerUp(): void {
        if (dragX === null) return;
        setOpen(dragX <= -THRESHOLD);
        setDragX(null);
    }

    function tapRow(): void {
        if (moved.current) return; // a swipe, not a tap
        if (open) {
            setOpen(false); // first tap closes a revealed row
            return;
        }
        hapticImpact("light");
        onEdit();
    }

    // GYM-153: full and short label keys for the middle PR marker.
    const [fullKey, shortKey] = set.is_pr ? prLabelKeys(set.pr_kind) : (["pr", "pr"] as const);

    return (
        <div className="relative overflow-hidden">
            {/* Delete action revealed behind the row (spec §11.3). */}
            <button
                type="button"
                onClick={onDelete}
                aria-label={t("setRow.deleteAria", { n: set.set })}
                className="absolute inset-y-0 right-0 flex items-center justify-center text-label font-semibold uppercase tracking-wide text-accent"
                style={{ width: `${REVEAL}px` }}
            >
                {t("common.delete")}
            </button>

            {/* GYM-153: containerType="inline-size" turns this row into a CSS
                @container so the PR chip label can collapse on narrow widths.
                The CSS lives in index.css: `.set-row-pr-full` / `.set-row-pr-short`. */}
            <div
                role="button"
                tabIndex={0}
                onClick={tapRow}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        hapticImpact("light");
                        onEdit();
                    }
                }}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onPointerCancel={onPointerUp}
                style={{
                    transform: `translateX(${offset}px)`,
                    containerType: "inline-size",
                }}
                className={`flex min-h-[44px] cursor-pointer touch-pan-y select-none items-center justify-between gap-4 bg-bg px-1 ${
                    dragX === null
                        ? "transition-transform duration-[180ms] ease-out-soft motion-reduce:transition-none"
                        : ""
                }`}
            >
                {/* Leading: SET N label. shrink-0 so it never compresses. */}
                <span className="shrink-0 text-label uppercase tracking-wide text-hint">
                    {t("set.n", { n: set.set })}
                </span>

                {/* GYM-153: middle zone — flex-1 center area. On PR rows holds
                    the marker chip; on non-PR rows it is an invisible spacer so
                    the trailing figure sits at the same right-aligned axis on both
                    PR and non-PR rows. The chip never displaces the figure. */}
                <div className="flex flex-1 items-center justify-center">
                    {set.is_pr ? (
                        <StatChip
                            className="animate-pr-pulse motion-reduce:animate-none"
                            aria-label={t(fullKey)}
                        >
                            {/*
                             * Container-query label collapse.
                             * .set-row-pr-full  = "Weight PR" / "Reps PR" (default)
                             * .set-row-pr-short = "PR" (fallback at ≤ 260px)
                             * Both spans always in DOM; CSS @container toggles which
                             * is visible — no JS measurement needed.
                             */}
                            <span className="set-row-pr-full">{t(fullKey)}</span>
                            <span className="set-row-pr-short">{t(shortKey)}</span>
                        </StatChip>
                    ) : null}
                </div>

                {/* Trailing: figure ONLY — chip removed (GYM-153). shrink-0 keeps
                    the figure from compressing. Its right edge is always anchored
                    at the same x, regardless of whether there is a PR chip. */}
                <div className="shrink-0">
                    <SetFigure weight={set.weight} reps={set.reps} />
                </div>
            </div>
        </div>
    );
}
