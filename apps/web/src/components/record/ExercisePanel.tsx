/**
 * Panel 2 of the picker slide track — the exercise step (spec §12.2 / §12.9,
 * extracted from RecordPicker.tsx in GYM-127). Pure presentation: the in-body
 * back control, the 2-column exercise tile grid with the "Show all" expander
 * (§12.9), the GYM-94 search-and-pick add field, the GYM-85 resolve hint and
 * the GYM-103 "Show Hidden" expander. All state and handlers live in
 * RecordPicker (the orchestrator).
 *
 * The panel is one 50%-wide slide-track child that scrolls internally; the
 * GYM-100 padding consumes --keyboard-pad from the BottomSheet panel so the
 * + Exercise add field and submit button stay visible above the keyboard.
 */
import { useT } from "@/i18n/catalog";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { ExerciseSearchField } from "./ExerciseSearchField";
import { PickerTile } from "./PickerTile";
import { ShowHiddenExpander } from "./ShowHiddenExpander";
import type { Exercise } from "@/api/analytics";

interface ExercisePanelProps {
    /** True while the slide track shows this (exercise) step. */
    isExerciseStep: boolean;
    selectedMuscle: string | null;
    /** Resolved numeric id of the selected muscle (search scope, GYM-94). */
    selectedMuscleId: number | null;
    onBack: () => void;
    exercisesLoading: boolean;
    exercisesError: boolean;
    onRetryExercises: () => void;
    /** Frequency-ordered visible slice of the catalog (GYM-83 / §12.9). */
    visibleExercises: Exercise[];
    /** How many more exercises the "Show all" tile reveals (0 = none). */
    hiddenCount: number;
    onShowAll: () => void;
    onPickExercise: (ex: Exercise) => void;
    onManageExercise: (ex: Exercise) => void;
    /** True while the add-exercise search field is open. */
    addingExercise: boolean;
    onOpenAddExercise: () => void;
    onCancelAddExercise: () => void;
    createPending: boolean;
    createError: boolean;
    /** Search-and-pick path — same as tapping a tile (GYM-94). */
    onSearchPick: (exerciseName: string) => void;
    /** Free-text create path (POST /exercises, GYM-85 resolution rules). */
    onCreateExercise: (name: string) => void;
    /** GYM-114: exercise ids the user already owns (search checkmarks). */
    ownedExerciseIds: Set<number>;
    /** GYM-85: non-blocking resolution=existing hint (null = none). */
    resolveHint: string | null;
    hiddenLoading: boolean;
    hiddenExercises: Exercise[];
    showHidden: boolean;
    onToggleHidden: () => void;
    /** The hidden-exercise id whose unhide mutation is in-flight (null = none). */
    pendingUnhideId: number | null;
    onManageHiddenExercise: (ex: Exercise) => void;
}

export function ExercisePanel({
    isExerciseStep,
    selectedMuscle,
    selectedMuscleId,
    onBack,
    exercisesLoading,
    exercisesError,
    onRetryExercises,
    visibleExercises,
    hiddenCount,
    onShowAll,
    onPickExercise,
    onManageExercise,
    addingExercise,
    onOpenAddExercise,
    onCancelAddExercise,
    createPending,
    createError,
    onSearchPick,
    onCreateExercise,
    ownedExerciseIds,
    resolveHint,
    hiddenLoading,
    hiddenExercises,
    showHidden,
    onToggleHidden,
    pendingUnhideId,
    onManageHiddenExercise,
}: ExercisePanelProps) {
    const { t, muscle } = useT();
    return (
        <div
            className="space-y-4"
            aria-hidden={!isExerciseStep}
            style={{
                width: "50%",
                minWidth: 0,
                overflowY: "auto",
                height: "100%",
                // GYM-100: consume --keyboard-pad from the BottomSheet panel so the
                // + Exercise add field and submit button are fully visible above the
                // keyboard from the moment the field opens, on a ~360px device.
                paddingBottom: "calc(max(var(--keyboard-pad, 0px), max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))) + 8px)",
                paddingRight: "4px",
            }}
        >
            {/* Back to muscles control (in-body; mirrors Phase B's "← Switch exercise"). */}
            <button
                type="button"
                tabIndex={isExerciseStep ? 0 : -1}
                onClick={onBack}
                className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
            >
                ← {selectedMuscle ? muscle(selectedMuscle) : t("picker.muscles")}
            </button>

            <h2 className="font-display text-title text-text">
                {selectedMuscle ? muscle(selectedMuscle) : ""}
            </h2>

            {/* Exercise tiles — 2-column grid, fixed height, line-clamp (GYM-77 #1/#3).
                GYM-83: source is the full catalog, ordered by frequency. */}
            {exercisesLoading ? (
                <div className="picker-tile-grid-exercise">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton
                            key={i}
                            className="h-tile w-full rounded-lg"
                        />
                    ))}
                </div>
            ) : exercisesError ? (
                <ErrorState
                    message={t("picker.loadExercisesError")}
                    onRetry={onRetryExercises}
                />
            ) : (
                <div className="picker-tile-grid-exercise">
                    {visibleExercises.map((ex) => (
                        <PickerTile
                            key={ex.id}
                            name={ex.name}
                            tabIndex={isExerciseStep ? 0 : -1}
                            onTap={() => onPickExercise(ex)}
                            onLongPress={() => onManageExercise(ex)}
                        />
                    ))}
                    {hiddenCount > 0 ? (
                        <button
                            type="button"
                            tabIndex={isExerciseStep ? 0 : -1}
                            onClick={onShowAll}
                            className="press-95 flex h-tile w-full items-center justify-center rounded-lg bg-accent-weak px-3 text-center text-base font-semibold text-accent"
                        >
                            {t("picker.showAll", { n: hiddenCount })}
                        </button>
                    ) : null}
                </div>
            )}

            {/* GYM-94: search-and-pick (add exercise).
                The ExerciseSearchField replaces the old bare AddInlineField:
                typing shows ranked canonical candidates first; free-text create
                is the last row (last resort). Picking a candidate calls onPick
                directly (same path as tapping a tile). Creating calls
                the existing POST /exercises path, unchanged. */}
            {addingExercise ? (
                <ExerciseSearchField
                    muscleName={selectedMuscle ?? ""}
                    muscleId={selectedMuscleId ?? 0}
                    pending={createPending}
                    error={createError ? t("picker.addError") : null}
                    onPick={onSearchPick}
                    onCreate={onCreateExercise}
                    onCancel={onCancelAddExercise}
                    tabIndex={isExerciseStep ? 0 : -1}
                    ownedIds={ownedExerciseIds}
                />
            ) : (
                <button
                    type="button"
                    tabIndex={isExerciseStep ? 0 : -1}
                    onClick={onOpenAddExercise}
                    className="press-95 min-h-[44px] rounded-full border border-dashed border-hairline px-4 text-base text-hint"
                >
                    {t("picker.addExercise")}
                </button>
            )}
            {/* GYM-85: non-blocking hint when resolution=existing.
                Shown in the exercise panel since both muscle and exercise
                "existing" cases navigate here (muscle pick transitions to
                exercises first, then the hint is set). */}
            {resolveHint ? (
                <p
                    aria-live="polite"
                    className="text-label text-hint"
                >
                    {resolveHint}
                </p>
            ) : null}

            {/* GYM-103: "Show Hidden" expander — bottom of exercise panel.
                Only rendered when there ARE hidden exercises for this muscle.
                Collapsed by default, reset when the muscle changes. */}
            <ShowHiddenExpander
                label={t("picker.showHiddenExercises")}
                isOpen={showHidden}
                onToggle={onToggleHidden}
                isLoading={hiddenLoading}
                hasHidden={hiddenExercises.length > 0}
                tabIndex={isExerciseStep ? 0 : -1}
            >
                <div className="picker-tile-grid-exercise">
                    {hiddenExercises.map((ex) => (
                        <PickerTile
                            key={ex.id}
                            muted
                            name={ex.name}
                            tabIndex={isExerciseStep ? 0 : -1}
                            isPending={pendingUnhideId === ex.id}
                            onLongPress={() => onManageHiddenExercise(ex)}
                        />
                    ))}
                </div>
            </ShowHiddenExpander>
        </div>
    );
}
