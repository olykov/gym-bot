/**
 * The one set row (spec §11.3 / §11.5) — extends the <ListRow> idea, reused for
 * every set in the day detail. Leading `Set {n}` (Sora --hint), trailing
 * `{weight}kg × {reps}` (Bebas-leaning, tabular-nums so rows align). ≥44px tall.
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
                style={{ transform: `translateX(${offset}px)` }}
                className={`flex min-h-[44px] cursor-pointer touch-pan-y select-none items-center justify-between gap-4 bg-bg px-1 ${
                    dragX === null
                        ? "transition-transform duration-[180ms] ease-out-soft motion-reduce:transition-none"
                        : ""
                }`}
            >
                <span className="text-label uppercase tracking-wide text-hint">
                    {t("set.n", { n: set.set })}
                </span>
                <SetFigure weight={set.weight} reps={set.reps} />
            </div>
        </div>
    );
}
