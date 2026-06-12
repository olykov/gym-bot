/**
 * Move-set sub-panel (GYM-51 §11.3 v2) — rendered inside SetEditor when the
 * user taps the "Move" action.
 *
 * Presents two optional move targets:
 *   1. New date — a native <input type="date"> (pre-filled with the current day).
 *   2. New exercise — a two-step muscle→exercise picker reusing the same tile
 *      pattern from RecordPicker (useMuscles + useTopMuscles for ordering,
 *      useTopExercises + useExercises for the exercise step).
 *
 * "Move" is enabled when at least one of {date, exercise} has changed from the
 * current values. Uses useMoveSet (which optimistically removes the set from the
 * source day cache, then invalidates both days on settle).
 *
 * GYM-143-v2 (content-sized model):
 * - Root div is plain flex-col — NO flex-1 / min-h-0 needed. The parent
 *   BottomSheet is content-sized (height:auto, max-height bounded via wrapper
 *   positioning above the nav). The sheet naturally grows to hug the content.
 * - Fields region is a plain flex-col; the body div in BottomSheet is
 *   overflow-y-auto and hits max-height if content is too tall — then the
 *   whole body scrolls. MOVE SET is outside the inner fields div so it stays
 *   visible at the panel's natural bottom.
 * - Date input: w-full min-w-0 on both wrapper and input prevents the native
 *   date widget from overflowing the right edge of the container on iOS/Android
 *   (retained from GYM-143 v1 — the intrinsic min-content width override).
 *
 * Errors:
 *   409 → "That slot is already taken — pick a different day or exercise."
 *   422/404 → "Couldn't move — check your selection."
 *
 * Token-only, mobile-first 360px, Chalk & Iron. No new library.
 */
import { useMemo, useState } from "react";
import { useT } from "@/i18n/catalog";
import type { TrainingSet } from "@/api/training";
import { ApiError } from "@/api/client";
import { hapticNotification } from "@/telegram/webapp";
import { useMoveSet } from "@/hooks/useTraining";
import {
    useMuscles,
    useTopMuscles,
    useTopExercises,
    useExercises,
} from "@/hooks/useAnalytics";
import { SheetSaveButton } from "@/components/ui/SheetSaveButton";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import type { Muscle, Exercise } from "@/api/analytics";

type MoveStep = "main" | "muscles" | "exercises";

interface MoveSetPanelProps {
    /** The day this set currently belongs to (YYYY-MM-DD). */
    date: string;
    /** Current exercise name (to detect if the exercise was changed). */
    exerciseName: string;
    /** Current muscle name (to detect if the exercise was changed). */
    muscleName: string;
    /** The set being moved (training_id is the mutation key). */
    set: TrainingSet;
    /** Called when the move completes (parent closes editor). */
    onMoved: () => void;
    /** Called when the user cancels (returns to edit mode). */
    onCancel: () => void;
}

export function MoveSetPanel({
    date,
    exerciseName,
    muscleName,
    set,
    onMoved,
    onCancel,
}: MoveSetPanelProps) {
    const { t, muscle } = useT();
    const [step, setStep] = useState<MoveStep>("main");

    // Target date (YYYY-MM-DD); starts as current day.
    const [targetDate, setTargetDate] = useState(date);
    // Target exercise; null means "same as current".
    const [targetMuscle, setTargetMuscle] = useState<string | null>(null);
    const [targetExercise, setTargetExercise] = useState<string | null>(null);

    // Mid-picker selection state.
    const [pickerMuscle, setPickerMuscle] = useState<string | null>(null);

    const [error, setError] = useState<string | null>(null);

    const moveSet = useMoveSet(date);

    // Determine if anything has actually changed.
    const dateChanged = targetDate !== date;
    const exerciseChanged =
        targetExercise !== null &&
        (targetExercise !== exerciseName || targetMuscle !== muscleName);
    const canMove =
        (dateChanged || exerciseChanged) && !moveSet.isPending;

    function submit(): void {
        if (!canMove) return;
        setError(null);
        const body: { date?: string; muscle_name?: string; exercise_name?: string } = {};
        if (dateChanged) body.date = targetDate;
        if (exerciseChanged && targetMuscle && targetExercise) {
            body.muscle_name = targetMuscle;
            body.exercise_name = targetExercise;
        }
        moveSet.mutate(
            {
                trainingId: set.training_id,
                body,
                targetDate: dateChanged ? targetDate : undefined,
            },
            {
                onSuccess: () => {
                    hapticNotification("success");
                    onMoved();
                },
                onError: (err) => {
                    if (err instanceof ApiError && err.status === 409) {
                        setError(t("move.slotTaken"));
                    } else if (
                        err instanceof ApiError &&
                        (err.status === 422 || err.status === 404)
                    ) {
                        setError(t("move.checkSelection"));
                    } else {
                        setError(t("move.error"));
                    }
                },
            },
        );
    }

    // Exercise-picker sub-steps. With content-sized BottomSheet, these render
    // as plain flex-col blocks; the BottomSheet body (overflow-y:auto) handles
    // scrolling when the list exceeds the available height.
    if (step === "muscles") {
        return (
            <MusclePicker
                onBack={() => setStep("main")}
                onPick={(name) => {
                    setPickerMuscle(name);
                    setStep("exercises");
                }}
            />
        );
    }

    if (step === "exercises" && pickerMuscle) {
        return (
            <ExercisePicker
                muscleName={pickerMuscle}
                onBack={() => setStep("muscles")}
                onPick={(exName) => {
                    setTargetMuscle(pickerMuscle);
                    setTargetExercise(exName);
                    setStep("main");
                }}
            />
        );
    }

    // Main move panel.
    // GYM-143-v2: plain flex-col — no flex-1/min-h-0. The sheet (content-sized)
    // grows to hug this block. SheetSaveButton sits naturally after the fields.
    return (
        <div className="flex flex-col">
            {/* Fields block — no overflow:auto here; the BottomSheet body
               handles scrolling if the whole content exceeds max-height. */}
            <div className="flex flex-col">
                {/* Section label */}
                <p className="mb-4 text-label uppercase tracking-wide text-hint">
                    {t("move.title")}
                </p>

                {/* Date field — GYM-143: w-full min-w-0 on wrapper + input
                   prevents the native date widget from overflowing the right
                   edge of the container on iOS/Android. box-sizing:border-box
                   is set globally by Tailwind preflight but `min-w-0` is the
                   critical addition — it overrides the input's intrinsic
                   min-content width so `w-full` can constrain it correctly. */}
                <div className="mb-4 w-full min-w-0">
                    <label
                        htmlFor="move-date"
                        className="text-label uppercase tracking-wide text-hint"
                    >
                        {t("move.day")}
                    </label>
                    <input
                        id="move-date"
                        type="date"
                        value={targetDate}
                        onChange={(e) => setTargetDate(e.target.value)}
                        className="mt-2 min-h-[44px] w-full min-w-0 rounded-md border border-hairline bg-secondary-bg px-3 text-base text-text outline-none focus:border-accent"
                    />
                </div>

                {/* Exercise picker row */}
                <div className="mb-4">
                    <p className="mb-2 text-label uppercase tracking-wide text-hint">
                        {t("label.exercise")}
                    </p>
                    <button
                        type="button"
                        onClick={() => setStep("muscles")}
                        className="press-95 flex min-h-[44px] w-full items-center justify-between gap-3 rounded-md border border-hairline bg-secondary-bg px-3 text-left"
                    >
                        <span className="min-w-0 flex-1 truncate text-base text-text">
                            {targetExercise
                                ? `${targetExercise} (${muscle(targetMuscle ?? "")})`
                                : t("move.exerciseChange", { exercise: exerciseName })}
                        </span>
                        <span aria-hidden className="shrink-0 text-hint">
                            ›
                        </span>
                    </button>
                    {targetExercise ? (
                        <button
                            type="button"
                            onClick={() => {
                                setTargetMuscle(null);
                                setTargetExercise(null);
                            }}
                            className="press-95 mt-1 text-label text-hint"
                        >
                            {t("move.clearExercise")}
                        </button>
                    ) : null}
                </div>

                {error ? (
                    <div
                        aria-live="polite"
                        className="mb-4 rounded-md border border-hairline bg-secondary-bg px-3 py-2"
                    >
                        <p className="text-label text-accent">{error}</p>
                    </div>
                ) : null}

                {/* Cancel row — flex items-center justify-center for reliable
                   vertical centering on all Android WebViews (GYM-140). */}
                <button
                    type="button"
                    onClick={onCancel}
                    className="press-95 mb-2 flex min-h-[44px] w-full items-center justify-center rounded-md border border-hairline bg-bg text-base text-text"
                >
                    {t("common.cancel")}
                </button>
            </div>

            {/* MOVE SET footer — outside the fields block so it always appears
               right after the last field with no dead space.
               GYM-143-v2: because the sheet is content-sized and the wrapper is
               positioned above the nav, this button is guaranteed to be visible
               without any sticky trick or nav-offset. */}
            <SheetSaveButton
                label={moveSet.isPending ? t("move.moving") : t("move.moveSet")}
                onClick={submit}
                disabled={!canMove}
            />
        </div>
    );
}

// ── Inline muscle picker ──────────────────────────────────────────────────────

interface MusclePickerProps {
    onBack: () => void;
    onPick: (muscleName: string) => void;
}

function MusclePicker({ onBack, onPick }: MusclePickerProps) {
    const { t, muscle } = useT();
    const muscles = useMuscles();
    const topMuscles = useTopMuscles();

    const frequencyMap = useMemo((): Map<string, number> => {
        const map = new Map<string, number>();
        for (const m of topMuscles.data ?? []) {
            map.set(m.name, m.frequency);
        }
        return map;
    }, [topMuscles.data]);

    const sorted = useMemo((): Muscle[] => {
        const catalog = muscles.data ?? [];
        return [...catalog].sort((a, b) => {
            const fa = frequencyMap.get(a.name) ?? 0;
            const fb = frequencyMap.get(b.name) ?? 0;
            if (fb !== fa) return fb - fa;
            return a.name.localeCompare(b.name);
        });
    }, [muscles.data, frequencyMap]);

    // GYM-143-v2: plain flex-col, no flex-1/min-h-0. The BottomSheet body
    // scrolls this whole block if it exceeds max-height.
    return (
        <div className="flex flex-col">
            <button
                type="button"
                onClick={onBack}
                className="press-95 -ml-1 mb-3 inline-flex shrink-0 min-h-[44px] items-center gap-1 px-1 text-base text-hint"
            >
                ← {t("common.back")}
            </button>
            <p className="mb-3 text-label uppercase tracking-wide text-hint">
                {t("move.targetMuscle")}
            </p>
            {muscles.isLoading ? (
                <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-[52px] w-full rounded-md" />
                    ))}
                </div>
            ) : muscles.isError ? (
                <ErrorState
                    message={t("picker.loadMusclesError")}
                    onRetry={() => void muscles.refetch()}
                />
            ) : (
                <div className="space-y-1">
                    {sorted.map((m) => (
                        <button
                            key={m.id}
                            type="button"
                            onClick={() => onPick(m.name)}
                            className="press-95 flex min-h-[52px] w-full items-center rounded-md border border-hairline bg-secondary-bg px-4 text-left text-base text-text"
                        >
                            {muscle(m.name)}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

// ── Inline exercise picker ────────────────────────────────────────────────────

interface ExercisePickerProps {
    muscleName: string;
    onBack: () => void;
    onPick: (exerciseName: string) => void;
}

function ExercisePicker({ muscleName, onBack, onPick }: ExercisePickerProps) {
    const { t, muscle } = useT();
    const muscles = useMuscles();
    const topExercises = useTopExercises(muscleName);

    const muscleId = useMemo((): number | null => {
        return (
            muscles.data?.find((m) => m.name === muscleName)?.id ?? null
        );
    }, [muscles.data, muscleName]);

    const fullExercises = useExercises(muscleId);

    const frequencyMap = useMemo((): Map<string, number> => {
        const map = new Map<string, number>();
        for (const ex of topExercises.data ?? []) {
            map.set(ex.name, ex.frequency);
        }
        return map;
    }, [topExercises.data]);

    const sorted = useMemo((): Exercise[] => {
        const catalog = fullExercises.data ?? [];
        return [...catalog].sort((a, b) => {
            const fa = frequencyMap.get(a.name) ?? 0;
            const fb = frequencyMap.get(b.name) ?? 0;
            if (fb !== fa) return fb - fa;
            return a.name.localeCompare(b.name);
        });
    }, [fullExercises.data, frequencyMap]);

    // GYM-143-v2: plain flex-col, no flex-1/min-h-0.
    return (
        <div className="flex flex-col">
            <button
                type="button"
                onClick={onBack}
                className="press-95 -ml-1 mb-3 inline-flex shrink-0 min-h-[44px] items-center gap-1 px-1 text-base text-hint"
            >
                ← {muscle(muscleName)}
            </button>
            <p className="mb-3 text-label uppercase tracking-wide text-hint">
                {t("move.targetExercise")}
            </p>
            {fullExercises.isLoading ? (
                <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-[52px] w-full rounded-md" />
                    ))}
                </div>
            ) : fullExercises.isError ? (
                <ErrorState
                    message={t("picker.loadExercisesError")}
                    onRetry={() => void fullExercises.refetch()}
                />
            ) : (
                <div className="space-y-1">
                    {sorted.map((ex) => (
                        <button
                            key={ex.id}
                            type="button"
                            onClick={() => onPick(ex.name)}
                            className="press-95 flex min-h-[52px] w-full items-center rounded-md border border-hairline bg-secondary-bg px-4 text-left text-base text-text"
                        >
                            {ex.name}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
