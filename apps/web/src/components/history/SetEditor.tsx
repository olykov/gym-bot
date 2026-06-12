/**
 * The set editor (spec §11.4, GYM-51 v2) — the contents of the <BottomSheet>.
 * Two <Stepper>s (Weight / Reps), a pinned SAVE button, a secondary two-step
 * Delete confirm, and a "Move" action (GYM-51).
 *
 * Modes:
 *   "edit"  — default, shows weight/reps steppers + Save + Delete
 *   "move"  — tapping "Move" swaps the body for <MoveSetPanel>; header stays.
 *   "confirmDelete" — in-sheet confirm before delete
 *
 * GYM-143 (root-cause fix): SetEditor's parent <BottomSheet> now uses
 * fixedHeight=true. The root div is flex-col flex-1 min-h-0, filling the
 * fixed panel body. The body region (mode-specific content) is flex-1
 * min-h-0 overflow-y-auto so it scrolls internally if needed. SheetSaveButton
 * uses mt-auto to anchor at the bottom of its flex column — short content
 * → SAVE pinned at panel bottom (no dead space); tall content → SAVE scrolls
 * into view below the last field (no overlap, no clipping). No sticky needed.
 *
 * Delete is never one-tap: tapping the header "Delete" swaps in an in-sheet
 * "Delete this set?" Cancel/Delete confirm with a warning haptic (§11.4).
 * The accent Delete lives in the HEADER row, spatially separated from the
 * bottom SAVE so it is not mis-tapped (§11.7).
 *
 * GYM-140 fixes (retained):
 * - Confirm buttons: `flex items-center justify-center` for reliable vertical
 *   text centering across all Android WebViews.
 * - Delete button in confirm step: `bg-accent text-button-text` (solid fill).
 * - Header Move/Delete triggers: no negative margins that could cause clipping.
 */
import { useEffect, useMemo, useState } from "react";
import { useT } from "@/i18n/catalog";
import type { TrainingSet } from "@/api/training";
import { hapticNotification } from "@/telegram/webapp";
import { useDeleteSet, useEditSet } from "@/hooks/useTraining";
import { useWeightRepsForm } from "@/hooks/useWeightRepsForm";
import { Stepper } from "@/components/ui/Stepper";
import { SheetSaveButton } from "@/components/ui/SheetSaveButton";
import { MoveSetPanel } from "./MoveSetPanel";

type EditorMode = "edit" | "move" | "confirmDelete";

export interface EditorTarget {
    set: TrainingSet;
    exerciseName: string;
    muscleName: string;
}

interface SetEditorProps {
    date: string;
    target: EditorTarget;
    titleId: string;
    onClose: () => void;
    /** Called after a delete settles (so the page can navigate back if empty). */
    onDeleted: () => void;
    /**
     * GYM-52: called when an edit mutation errors out (after optimistic
     * rollback). The parent surfaces the "couldn't save — restored" message.
     */
    onEditError?: () => void;
    /**
     * GYM-52: called when a delete mutation errors out (after optimistic
     * rollback). The parent surfaces the "couldn't delete — restored" message.
     */
    onDeleteError?: () => void;
}

export function SetEditor({
    date,
    target,
    titleId,
    onClose,
    onDeleted,
    onEditError,
    onDeleteError,
}: SetEditorProps) {
    const { t } = useT();
    const { set, exerciseName, muscleName } = target;

    // GYM-126: shared weight/reps form mechanics; the changed-from-original
    // check below is this editor's own semantic, composed on top.
    const form = useWeightRepsForm({
        weightText: String(set.weight),
        repsText: String(set.reps),
    });
    const { weight, reps, valid, reset } = form;
    const [mode, setMode] = useState<EditorMode>("edit");

    const edit = useEditSet(date);
    const del = useDeleteSet(date);

    const changed = weight !== set.weight || reps !== set.reps;
    const canSave = valid && changed && !edit.isPending && !del.isPending;

    // Reset local state when the target set changes (sheet re-used for a new row).
    useEffect(() => {
        reset({
            weightText: String(set.weight),
            repsText: String(set.reps),
        });
        setMode("edit");
    }, [reset, set.training_id, set.weight, set.reps]);

    function save(): void {
        if (!canSave || weight === null || reps === null) return;
        edit.mutate(
            { trainingId: set.training_id, body: { weight, reps } },
            {
                onSuccess: () => hapticNotification("success"),
                onError: () => onEditError?.(),
            },
        );
        // Optimistic: the onMutate cache patch already applied, so close
        // immediately; the success haptic still fires on settle.
        onClose();
    }

    function startDelete(): void {
        hapticNotification("warning");
        setMode("confirmDelete");
    }

    function confirmDelete(): void {
        del.mutate(set.training_id, {
            onSuccess: () => hapticNotification("success"),
            onError: () => onDeleteError?.(),
        });
        onClose();
        onDeleted();
    }

    const headerSub = useMemo(
        () => t("set.n", { n: set.set }),
        [t, set.set],
    );

    // GYM-143: root is flex-col flex-1 min-h-0 — fills the fixedHeight panel
    // body (which is itself flex-col). Header is shrink-0 at the top; the body
    // region (edit/confirm/move) is flex-1 min-h-0 overflow-y-auto so tall
    // content scrolls internally. SheetSaveButton uses mt-auto (built into the
    // component) to anchor at the flex bottom — short content: SAVE pinned at
    // panel bottom; tall content: SAVE after last field, scrolls into view.
    return (
        <div className="flex min-h-0 flex-1 flex-col">
            {/* Header row: read-only identity (§11.4) + Delete + Move actions.
               Both Delete and Move live HERE, in the header, spatially separated
               from the bottom SAVE so they are not mis-tapped (§11.7).
               GYM-140: no negative margins; inline-flex + items-center for
               reliable vertical centering on Android WebViews. */}
            <div className="mb-4 flex shrink-0 items-start justify-between gap-3">
                <div className="min-w-0">
                    <h2
                        id={titleId}
                        className="truncate text-base font-semibold text-text"
                    >
                        {exerciseName}
                    </h2>
                    <p className="text-label uppercase tracking-wide text-hint">
                        {headerSub}
                    </p>
                </div>

                {/* Delete + Move triggers — accent text, sparing per §9.3; ≥44px tap.
                    Hidden during the delete-confirm step to keep the UI clean. */}
                {mode === "edit" && (
                    <div className="flex shrink-0 items-center gap-1">
                        {/* Move button (GYM-51) */}
                        <button
                            type="button"
                            onClick={() => setMode("move")}
                            className="press-95 inline-flex min-h-[44px] items-center gap-1 px-2 text-base text-accent"
                            aria-label={t("editor.moveSetAria", {
                                exercise: exerciseName,
                                n: set.set,
                            })}
                        >
                            <MoveIcon />
                            {t("editor.move")}
                        </button>

                        {/* Delete trigger */}
                        <button
                            type="button"
                            onClick={startDelete}
                            className="press-95 inline-flex min-h-[44px] items-center gap-1 px-2 text-base text-accent"
                            aria-label={t("editor.deleteSetAria", {
                                exercise: exerciseName,
                                n: set.set,
                            })}
                        >
                            <TrashIcon />
                            {t("common.delete")}
                        </button>
                    </div>
                )}
            </div>

            {/* Body region: flex-1 min-h-0 overflow-y-auto — all mode-specific
               content scrolls internally if it exceeds the available height.
               GYM-143: this is the scroll container, NOT the panel body, so
               SheetSaveButton's mt-auto is relative to the flex column here. */}
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
                {/* Two-step confirm (§11.4 / §11.7). GYM-140: buttons use
                   `flex items-center justify-center`; Delete is `bg-accent
                   text-button-text` (solid fill) for clear visibility. */}
                {mode === "confirmDelete" && (
                    <>
                        <div className="rounded-md border border-hairline bg-secondary-bg p-4">
                            <p className="mb-4 text-base text-text">
                                {t("editor.deleteThisSet")}
                            </p>
                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setMode("edit")}
                                    className="press-95 flex min-h-[48px] flex-1 items-center justify-center rounded-md border border-hairline bg-bg text-base text-text"
                                >
                                    {t("common.cancel")}
                                </button>
                                <button
                                    type="button"
                                    onClick={confirmDelete}
                                    disabled={del.isPending}
                                    className="press-95 flex min-h-[48px] flex-1 items-center justify-center rounded-md bg-accent text-base font-semibold text-button-text disabled:opacity-50"
                                >
                                    {t("common.delete")}
                                </button>
                            </div>
                        </div>
                    </>
                )}

                {mode === "edit" && (
                    <>
                        <div className="flex flex-col gap-6">
                            <Stepper
                                label={t("label.weight")}
                                unit={t("unit.kg")}
                                {...form.weightProps}
                            />
                            <Stepper label={t("label.reps")} {...form.repsProps} />
                        </div>

                        {/* GYM-143: mt-auto wrapper pushes SAVE to the bottom
                           of this flex column. Short content → SAVE at panel
                           bottom, no dead space. Tall content → scrolls into
                           view after the last stepper, no clipping/overlap. */}
                        <div className="mt-auto">
                            <SheetSaveButton
                                label={t("common.save")}
                                onClick={save}
                                disabled={!canSave}
                            />
                        </div>
                    </>
                )}

                {/* Move mode — header is retained above; MoveSetPanel fills
                   the body region (it is also flex-col flex-1 min-h-0). */}
                {mode === "move" && (
                    <MoveSetPanel
                        date={date}
                        exerciseName={exerciseName}
                        muscleName={muscleName}
                        set={set}
                        onMoved={() => {
                            onClose();
                            onDeleted();
                        }}
                        onCancel={() => setMode("edit")}
                    />
                )}
            </div>
        </div>
    );
}

/** Small move/transfer glyph (two arrows, token-stroked, currentColor). */
function MoveIcon() {
    return (
        <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
        >
            <path d="M5 9l4-4-4-4" />
            <path d="M9 5H3" />
            <path d="M19 15l-4 4 4 4" />
            <path d="M15 19h6" />
            <path d="M3 15h8M13 9h8" />
        </svg>
    );
}

/** Small trash glyph (token-stroked, inherits accent via currentColor). */
function TrashIcon() {
    return (
        <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
        >
            <path d="M3 6h18" />
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14" />
            <path d="M10 11v6M14 11v6" />
        </svg>
    );
}
