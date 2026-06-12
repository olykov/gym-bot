/**
 * The set editor (spec §11.4, GYM-51 v2) — the contents of the <BottomSheet>.
 * Two <Stepper>s (Weight / Reps), a sticky in-sheet SAVE button, a secondary
 * two-step Delete confirm, and a new "Move" action (GYM-51).
 *
 * Modes:
 *   "edit"  — default, shows weight/reps steppers + Save + Delete (unchanged)
 *   "move"  — tapping "Move" swaps the body for <MoveSetPanel>; header stays.
 *   "confirmDelete" — in-sheet confirm before delete (unchanged)
 *
 * Edit + delete are optimistic via the useTraining mutations; move is via
 * useMoveSet (optimistic removal from source day). The parent owns the day
 * `date` (the query key) and the close.
 *
 * Validation (§11.7): Save is enabled only when weight & reps are valid
 * (non-empty, non-negative, reps integer) AND changed from the original.
 * Weight steps 2.5kg and accepts decimals (comma-normalized); reps is integer.
 *
 * SAVE is an in-sheet sticky button (`position:sticky; bottom:0`), NOT the
 * Telegram native MainButton (GYM-54). The MainButton overlaid the WebApp
 * viewport bottom and, inside a bottom-sheet, clipped the sheet's lowest field
 * on real devices (it caused GYM-53 #1 + this bug). The sticky button stays
 * pinned to the bottom of the sheet's scroll viewport, above the safe-area, so
 * Weight + Reps + Save + Delete are all reachable and nothing is ever clipped.
 *
 * Delete is never one-tap: tapping the header "Delete" control swaps in an
 * in-sheet "Delete this set?" Cancel/Delete confirm with a warning haptic
 * (§11.4). The accent Delete lives in the HEADER row, spatially separated from
 * the bottom SAVE so it is not mis-tapped.
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
                // GYM-52: rollback is silent without this — notify the parent so
                // it can surface "Couldn't save — restored." to the user.
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
            // GYM-52: rollback is silent without this — notify the parent so
            // it can surface "Couldn't delete — restored." to the user.
            onError: () => onDeleteError?.(),
        });
        // Optimistic: the onMutate cache patch has already removed the row, so
        // close and let the page decide (from the live cache) whether the day
        // is now empty and it should navigate back (spec §11.3).
        onClose();
        onDeleted();
    }

    const headerSub = useMemo(
        () => t("set.n", { n: set.set }),
        [t, set.set],
    );

    // Move mode — delegates entirely to MoveSetPanel.
    if (mode === "move") {
        return (
            <div>
                {/* Header retained in move mode so the user knows which set. */}
                <div className="mb-4 min-w-0">
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
                <MoveSetPanel
                    date={date}
                    exerciseName={exerciseName}
                    muscleName={muscleName}
                    set={set}
                    onMoved={() => {
                        onClose();
                        onDeleted(); // the set left the source day — same post-delete check
                    }}
                    onCancel={() => setMode("edit")}
                />
            </div>
        );
    }

    return (
        <div>
            {/* Header row: read-only identity (§11.4) + Delete + Move actions.
               Both Delete and Move live HERE, in the header, spatially separated
               from the bottom SAVE so they are not mis-tapped (§11.7). */}
            <div className="mb-4 flex items-start justify-between gap-3">
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
                            className="press-95 -mr-1 inline-flex min-h-[44px] items-center gap-1 px-2 text-base text-accent"
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
                            className="press-95 -mr-2 inline-flex min-h-[44px] items-center gap-1 px-2 text-base text-accent"
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

            {/* Two-step confirm (§11.4 / §11.7) — rendered high, under the
               header, separated from the sticky SAVE. */}
            {mode === "confirmDelete" && (
                <div className="mb-5 rounded-md border border-hairline bg-secondary-bg p-3">
                    <p className="text-base text-text">
                        {t("editor.deleteThisSet")}
                    </p>
                    <div className="mt-3 flex gap-2">
                        <button
                            type="button"
                            onClick={() => setMode("edit")}
                            className="press-95 min-h-[44px] flex-1 rounded-md border border-hairline bg-bg text-base text-text"
                        >
                            {t("common.cancel")}
                        </button>
                        <button
                            type="button"
                            onClick={confirmDelete}
                            disabled={del.isPending}
                            className="press-95 min-h-[44px] flex-1 rounded-md bg-accent-weak text-base font-semibold text-accent disabled:opacity-50"
                        >
                            {t("common.delete")}
                        </button>
                    </div>
                </div>
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

                    {/* Sticky in-sheet SAVE (§11.4, GYM-54) — the shared
                       <SheetSaveButton>, pinned to the bottom of the sheet's scroll
                       viewport so it never clips (replaces the native MainButton).
                       Disabled when unchanged/invalid (same logic as before). */}
                    <SheetSaveButton
                        label={t("common.save")}
                        onClick={save}
                        disabled={!canSave}
                    />
                </>
            )}
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
