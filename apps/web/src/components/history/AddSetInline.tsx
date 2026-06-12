/**
 * Inline add-set affordance (GYM-51 §11.3 v2).
 *
 * Renders as a quiet "+ Add set" row below the last <SetRow> of an exercise
 * group. Tapping expands to an inline weight/reps entry (two <Stepper>s) with
 * an "Add" (<SheetSaveButton> style) and a "Cancel". On confirm, calls
 * useAddSet with the next set number (max(existing set #s) + 1). Collapses
 * back on cancel or on success.
 *
 * Pre-fill: weight + reps from the LAST set of this exercise on this day (the
 * most convenient anchor for "I forgot to log set 3"). If no sets exist yet
 * (edge-case), fields start empty.
 *
 * Token-only (spacing 4/8/12/16/24/32, color via §3+§9.3 vars), ≥44px touch
 * targets, Chalk & Iron aesthetic. No new library.
 */
import { useState } from "react";
import { useT } from "@/i18n/catalog";
import type { TrainingSet } from "@/api/training";
import { hapticNotification } from "@/telegram/webapp";
import { useAddSet } from "@/hooks/useTraining";
import { useWeightRepsForm } from "@/hooks/useWeightRepsForm";
import { Stepper } from "@/components/ui/Stepper";
import { ApiError } from "@/api/client";

interface AddSetInlineProps {
    /** The date string for this day (YYYY-MM-DD). */
    date: string;
    /** Muscle group name — passed directly to TrainingCreate. */
    muscleName: string;
    /** Exercise name — passed directly to TrainingCreate. */
    exerciseName: string;
    /** All sets currently in this exercise group — used to derive the next set#. */
    existingSets: TrainingSet[];
    /** Called after a successful add so the parent can refresh. */
    onAdded?: () => void;
}

export function AddSetInline({
    date,
    muscleName,
    exerciseName,
    existingSets,
    onAdded,
}: AddSetInlineProps) {
    const { t } = useT();
    const [open, setOpen] = useState(false);

    // Pre-fill from the last (highest set-number) set on this day.
    const lastSet =
        existingSets.length > 0
            ? existingSets.reduce((best, s) => (s.set > best.set ? s : best))
            : null;

    // GYM-126: shared weight/reps form mechanics; the lastSet pre-fill (here
    // and re-applied in openForm) is this component's own semantic.
    const form = useWeightRepsForm({
        weightText: lastSet ? String(lastSet.weight) : "",
        repsText: lastSet ? String(lastSet.reps) : "",
    });
    const { weight, reps } = form;
    const [error, setError] = useState<string | null>(null);

    const addSet = useAddSet(date);

    // Next set number = max existing + 1 (computed fresh from props each render).
    const nextSet =
        existingSets.length > 0
            ? Math.max(...existingSets.map((s) => s.set)) + 1
            : 1;

    const valid = form.valid && !addSet.isPending;

    function openForm(): void {
        // Reset pre-fill from current existingSets each time the form opens.
        const last =
            existingSets.length > 0
                ? existingSets.reduce((best, s) =>
                      s.set > best.set ? s : best,
                  )
                : null;
        form.reset({
            weightText: last ? String(last.weight) : "",
            repsText: last ? String(last.reps) : "",
        });
        setError(null);
        setOpen(true);
    }

    function cancel(): void {
        setOpen(false);
        setError(null);
    }

    function submit(): void {
        if (!valid || weight === null || reps === null) return;
        setError(null);
        addSet.mutate(
            {
                body: {
                    muscle_name: muscleName,
                    exercise_name: exerciseName,
                    set: nextSet,
                    weight,
                    reps,
                    date,
                },
            },
            {
                onSuccess: () => {
                    hapticNotification("success");
                    setOpen(false);
                    onAdded?.();
                },
                onError: (err) => {
                    if (err instanceof ApiError && err.status === 409) {
                        setError(t("addSet.exists"));
                    } else {
                        setError(t("addSet.error"));
                    }
                },
            },
        );
    }

    if (!open) {
        return (
            <button
                type="button"
                onClick={openForm}
                className="press-95 -mx-1 flex min-h-[44px] w-full items-center gap-2 rounded-md px-1 text-label text-hint"
                aria-label={t("addSet.triggerAria", { exercise: exerciseName })}
            >
                <span
                    aria-hidden
                    className="text-base leading-none"
                >
                    +
                </span>
                {t("addSet.trigger")}
            </button>
        );
    }

    return (
        <div className="mt-2 rounded-md border border-hairline bg-secondary-bg p-3">
            {/* Compact label */}
            <p className="mb-3 text-label uppercase tracking-wide text-hint">
                {t("set.n", { n: nextSet })}
            </p>

            <div className="flex flex-col gap-4">
                <Stepper
                    label={t("label.weight")}
                    unit={t("unit.kg")}
                    {...form.weightProps}
                />
                <Stepper label={t("label.reps")} {...form.repsProps} />
            </div>

            {error ? (
                <div
                    aria-live="polite"
                    className="mt-3 rounded-md border border-hairline bg-bg px-3 py-2"
                >
                    <p className="text-label text-accent">{error}</p>
                </div>
            ) : null}

            <div className="mt-4 flex gap-2">
                <button
                    type="button"
                    onClick={cancel}
                    disabled={addSet.isPending}
                    className="press-95 min-h-[44px] flex-1 rounded-md border border-hairline bg-bg text-base text-text disabled:opacity-50"
                >
                    {t("common.cancel")}
                </button>
                <button
                    type="button"
                    onClick={submit}
                    disabled={!valid}
                    className="press-95 min-h-[44px] flex-1 rounded-md bg-accent text-base font-semibold uppercase tracking-wide text-button-text disabled:cursor-not-allowed disabled:opacity-40"
                >
                    {addSet.isPending ? t("addSet.adding") : t("common.add")}
                </button>
            </div>
        </div>
    );
}
