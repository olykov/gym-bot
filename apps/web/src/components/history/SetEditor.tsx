/**
 * The set editor (spec §11.4) — the contents of the <BottomSheet>. Two
 * <Stepper>s (Weight / Reps), a Telegram MainButton SAVE, and a secondary
 * two-step Delete confirm. Edit + delete are optimistic via the useTraining
 * mutations; the parent owns the day `date` (the query key) and the close.
 *
 * Validation (§11.7): Save is enabled only when weight & reps are valid
 * (non-empty, non-negative, reps integer) AND changed from the original.
 * Weight steps 2.5kg and accepts decimals (comma-normalized); reps is integer.
 *
 * Delete is never one-tap: tapping "Delete set" swaps the footer to an in-sheet
 * "Delete this set?" Cancel/Delete confirm with a warning haptic (§11.4).
 */
import { useEffect, useMemo, useState } from "react";
import type { TrainingSet } from "@/api/training";
import {
    hapticNotification,
    mainButton,
} from "@/telegram/webapp";
import { useDeleteSet, useEditSet } from "@/hooks/useTraining";
import { Divider } from "@/components/ui/Divider";
import { Stepper, parseNumeric } from "@/components/ui/Stepper";

export interface EditorTarget {
    set: TrainingSet;
    exerciseName: string;
}

interface SetEditorProps {
    date: string;
    target: EditorTarget;
    titleId: string;
    onClose: () => void;
    /** Called after a delete settles (so the page can navigate back if empty). */
    onDeleted: () => void;
}

export function SetEditor({
    date,
    target,
    titleId,
    onClose,
    onDeleted,
}: SetEditorProps) {
    const { set, exerciseName } = target;

    const [weightText, setWeightText] = useState(String(set.weight));
    const [repsText, setRepsText] = useState(String(set.reps));
    const [confirmingDelete, setConfirmingDelete] = useState(false);

    const edit = useEditSet(date);
    const del = useDeleteSet(date);

    const weight = parseNumeric(weightText, false);
    const reps = parseNumeric(repsText, true);

    const valid =
        weight !== null && weight >= 0 && reps !== null && reps >= 0;
    const changed = weight !== set.weight || reps !== set.reps;
    const canSave = valid && changed && !edit.isPending && !del.isPending;

    // Reset local state when the target set changes (sheet re-used for a new row).
    useEffect(() => {
        setWeightText(String(set.weight));
        setRepsText(String(set.reps));
        setConfirmingDelete(false);
    }, [set.training_id, set.weight, set.reps]);

    function save(): void {
        if (!canSave || weight === null || reps === null) return;
        mainButton.showProgress();
        edit.mutate(
            { trainingId: set.training_id, body: { weight, reps } },
            {
                onSuccess: () => {
                    hapticNotification("success");
                    onClose(); // optimistic UI already patched the row
                },
                onError: () => {
                    mainButton.hideProgress();
                },
            },
        );
        // Optimistic: close immediately; the success/err haptic still fires.
        onClose();
    }

    // Telegram MainButton drives SAVE (spec §11.4): show/enable on validity,
    // hide on unmount. The handler is kept fresh via the effect deps.
    useEffect(() => {
        mainButton.show("SAVE");
        mainButton.setEnabled(canSave);
        const teardown = mainButton.onClick(save);
        return teardown;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canSave, weightText, repsText, set.training_id]);

    function startDelete(): void {
        hapticNotification("warning");
        setConfirmingDelete(true);
    }

    function confirmDelete(): void {
        mainButton.hide();
        del.mutate(set.training_id, {
            onSuccess: () => hapticNotification("success"),
        });
        // Optimistic: the onMutate cache patch has already removed the row, so
        // close and let the page decide (from the live cache) whether the day
        // is now empty and it should navigate back (spec §11.3).
        onClose();
        onDeleted();
    }

    const headerSub = useMemo(() => `Set ${set.set}`, [set.set]);

    return (
        <div>
            {/* Read-only identity (spec §11.4): exercise + set #, not editable. */}
            <div className="mb-4">
                <h2 id={titleId} className="text-base font-semibold text-text">
                    {exerciseName}
                </h2>
                <p className="text-label uppercase tracking-wide text-hint">
                    {headerSub}
                </p>
            </div>

            <div className="flex flex-col gap-6">
                <Stepper
                    label="Weight"
                    unit="kg"
                    value={weight}
                    text={weightText}
                    onChange={({ text }) => setWeightText(text)}
                    min={0}
                    step={2.5}
                    inputMode="decimal"
                />
                <Stepper
                    label="Reps"
                    value={reps}
                    text={repsText}
                    onChange={({ text }) => setRepsText(text)}
                    min={0}
                    step={1}
                    integer
                    inputMode="numeric"
                />
            </div>

            <Divider className="my-4" />

            {/* Delete: two-step in-sheet confirm (spec §11.4 / §11.7). */}
            {confirmingDelete ? (
                <div>
                    <p className="text-base text-text">Delete this set?</p>
                    <div className="mt-3 flex gap-2">
                        <button
                            type="button"
                            onClick={() => setConfirmingDelete(false)}
                            className="press-95 min-h-[44px] flex-1 rounded-md border border-hairline bg-bg text-base text-text"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            onClick={confirmDelete}
                            disabled={del.isPending}
                            className="press-95 min-h-[44px] flex-1 rounded-md bg-accent-weak text-base font-semibold text-accent disabled:opacity-50"
                        >
                            Delete
                        </button>
                    </div>
                </div>
            ) : (
                <button
                    type="button"
                    onClick={startDelete}
                    className="press-95 min-h-[44px] w-full text-center text-base text-accent"
                >
                    Delete set
                </button>
            )}
        </div>
    );
}
