/**
 * Brand-new-user prompt (spec §12.6, extracted from RecordPicker.tsx in
 * GYM-127): nothing trained today AND an empty catalog → a front-and-center
 * "ADD YOUR FIRST EXERCISE" flow inside the record sheet. Name a muscle first,
 * then an exercise under it (search-and-pick once the muscle id resolves,
 * GYM-94) — the controller swaps straight to Phase B after the pick.
 *
 * Pure presentation: every action and all pending/error state comes from
 * RecordPicker (the orchestrator), so the create/resolve semantics (GYM-85)
 * stay in one place.
 */
import { useT } from "@/i18n/catalog";
import { MUSCLE_NAME_MAX, EXERCISE_NAME_MAX } from "@/validation";
import { EmptyState } from "@/components/ui/EmptyState";
import { AddInlineField } from "./AddInlineField";
import { ExerciseSearchField } from "./ExerciseSearchField";

interface EmptyNewUserPromptProps {
    /** The just-created muscle (null until the user adds one). */
    selectedMuscle: string | null;
    /** Its id once the muscle catalog refreshed (null until then). */
    selectedMuscleId: number | null;
    muscleCreatePending: boolean;
    muscleCreateError: boolean;
    exerciseCreatePending: boolean;
    exerciseCreateError: boolean;
    /** GYM-85: non-blocking resolution=existing hint (null = none). */
    resolveHint: string | null;
    /** GYM-114: exercise ids the user already owns (search checkmarks). */
    ownedExerciseIds: Set<number>;
    onSubmitMuscle: (name: string) => void;
    onSubmitExercise: (name: string) => void;
    /** Search-and-pick path — same as tapping a tile (GYM-94). */
    onPickExercise: (exerciseName: string) => void;
    /** Cancel the exercise step → back to the muscle field. */
    onCancelExercise: () => void;
}

export function EmptyNewUserPrompt({
    selectedMuscle,
    selectedMuscleId,
    muscleCreatePending,
    muscleCreateError,
    exerciseCreatePending,
    exerciseCreateError,
    resolveHint,
    ownedExerciseIds,
    onSubmitMuscle,
    onSubmitExercise,
    onPickExercise,
    onCancelExercise,
}: EmptyNewUserPromptProps) {
    const { t, muscle } = useT();
    return (
        <>
            <h2 className="font-display text-title text-text">
                {t("record.title")}
            </h2>
            <div className="mt-6">
                <EmptyState
                    title={t("emptyUser.title")}
                    subtitle={t("emptyUser.subtitle")}
                />
                <div className="mt-2 space-y-3">
                    {!selectedMuscle ? (
                        <AddInlineField
                            placeholder={t("emptyUser.musclePlaceholder")}
                            actionLabel={t("common.add")}
                            maxLength={MUSCLE_NAME_MAX}
                            pending={muscleCreatePending}
                            error={
                                muscleCreateError ? t("picker.addError") : null
                            }
                            onSubmit={onSubmitMuscle}
                        />
                    ) : selectedMuscleId !== null ? (
                        /* GYM-94: search-and-pick in the empty-new-user path.
                           Only when the muscle id is resolved (cache refreshed
                           after the create mutation) so the API call is scoped. */
                        <ExerciseSearchField
                            muscleName={selectedMuscle}
                            muscleId={selectedMuscleId}
                            pending={exerciseCreatePending}
                            error={
                                exerciseCreateError ? t("picker.addError") : null
                            }
                            onPick={onPickExercise}
                            onCreate={onSubmitExercise}
                            onCancel={onCancelExercise}
                            ownedIds={ownedExerciseIds}
                        />
                    ) : (
                        /* Fallback: muscle was just created but id not yet in
                           cache — use the plain add-inline until muscles reload. */
                        <AddInlineField
                            placeholder={t("emptyUser.exercisePlaceholder", {
                                muscle: muscle(selectedMuscle),
                            })}
                            actionLabel={t("common.add")}
                            maxLength={EXERCISE_NAME_MAX}
                            pending={exerciseCreatePending}
                            error={
                                exerciseCreateError ? t("picker.addError") : null
                            }
                            onSubmit={onSubmitExercise}
                            onCancel={onCancelExercise}
                        />
                    )}
                    {/* GYM-85: non-blocking hint when resolution=existing (empty-user path). */}
                    {resolveHint ? (
                        <p
                            aria-live="polite"
                            className="text-label text-hint"
                        >
                            {resolveHint}
                        </p>
                    ) : null}
                </div>
            </div>
        </>
    );
}
