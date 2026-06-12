/**
 * Panel 1 of the picker slide track — the muscle step (spec §12.2, extracted
 * from RecordPicker.tsx in GYM-127). Pure presentation: the Continue-today
 * tile, the 3-column muscle tile grid (+ add-inline trigger/field) and the
 * GYM-103 "Show Hidden" expander. All state and handlers live in RecordPicker
 * (the orchestrator).
 *
 * The panel is one 50%-wide slide-track child that scrolls internally; the
 * GYM-100 padding consumes --keyboard-pad from the BottomSheet panel so the
 * add-muscle field stays visible above the software keyboard.
 */
import { useT } from "@/i18n/catalog";
import { MUSCLE_NAME_MAX } from "@/validation";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { AddInlineField } from "./AddInlineField";
import { PickerTile } from "./PickerTile";
import { ShowHiddenExpander } from "./ShowHiddenExpander";
import type { Muscle } from "@/api/analytics";

/** The last exercise trained today (derived in RecordPicker). */
export interface ContinueExercise {
    muscleName: string;
    exerciseName: string;
}

interface MusclePanelProps {
    /** True while the slide track shows the exercise step (this panel is off). */
    isExerciseStep: boolean;
    dayLoading: boolean;
    continueExercise: ContinueExercise | null;
    onContinue: () => void;
    musclesLoading: boolean;
    musclesError: boolean;
    onRetryMuscles: () => void;
    muscleOptions: string[];
    onPickMuscle: (name: string) => void;
    onManageMuscle: (name: string) => void;
    /** True while the add-muscle inline field is open. */
    addingMuscle: boolean;
    onOpenAddMuscle: () => void;
    onCancelAddMuscle: () => void;
    createPending: boolean;
    createError: boolean;
    onSubmitMuscle: (name: string) => void;
    hiddenLoading: boolean;
    hiddenMuscles: Muscle[];
    showHidden: boolean;
    onToggleHidden: () => void;
    /** The hidden-muscle id whose unhide mutation is in-flight (null = none). */
    pendingUnhideId: number | null;
    onManageHiddenMuscle: (m: Muscle) => void;
}

export function MusclePanel({
    isExerciseStep,
    dayLoading,
    continueExercise,
    onContinue,
    musclesLoading,
    musclesError,
    onRetryMuscles,
    muscleOptions,
    onPickMuscle,
    onManageMuscle,
    addingMuscle,
    onOpenAddMuscle,
    onCancelAddMuscle,
    createPending,
    createError,
    onSubmitMuscle,
    hiddenLoading,
    hiddenMuscles,
    showHidden,
    onToggleHidden,
    pendingUnhideId,
    onManageHiddenMuscle,
}: MusclePanelProps) {
    const { t, muscle } = useT();
    return (
        <div
            className="space-y-4"
            aria-hidden={isExerciseStep}
            style={{
                width: "50%",
                minWidth: 0,
                overflowY: "auto",
                height: "100%",
                // GYM-100: consume --keyboard-pad from the BottomSheet panel so the
                // add-muscle field stays visible above the keyboard. Fallback to 8px
                // when no keyboard is up. Safe-area bottom ensures content clears the
                // device home indicator.
                paddingBottom: "calc(max(var(--keyboard-pad, 0px), max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))) + 8px)",
                paddingRight: "4px",
            }}
        >
            <h2 className="font-display text-title text-text">
                {t("record.title")}
            </h2>

            {/* Continue today tile (§12.2 v2). */}
            {dayLoading ? (
                <Skeleton className="h-[60px] w-full rounded-lg" />
            ) : continueExercise ? (
                <>
                    <button
                        type="button"
                        tabIndex={isExerciseStep ? -1 : 0}
                        onClick={onContinue}
                        className="press-95 flex min-h-[60px] w-full items-center justify-between gap-3 rounded-lg border border-hairline bg-secondary-bg px-4 py-3 text-left"
                    >
                        <span className="min-w-0">
                            <span className="block text-label uppercase tracking-wide text-hint">
                                {t("record.continueToday")}
                            </span>
                            <span className="mt-0.5 block truncate text-base font-semibold text-text">
                                {continueExercise.exerciseName}
                            </span>
                            <span className="block truncate text-label text-hint">
                                {muscle(continueExercise.muscleName)}
                            </span>
                        </span>
                        <span aria-hidden className="shrink-0 text-hint">
                            ›
                        </span>
                    </button>

                    {/* Very light, fading hairline — a whisper, not a hard cut. */}
                    <div
                        aria-hidden
                        className="record-divider-faint mx-auto h-px w-2/3"
                    />
                </>
            ) : null}

            {/* Muscle tiles — auto-fit grid so custom/long names don't break. */}
            <section className="space-y-3">
                <div className="text-label uppercase tracking-wide text-hint">
                    {t("label.muscle")}
                </div>

                {musclesError ? (
                    <ErrorState
                        message={t("picker.loadMusclesError")}
                        onRetry={onRetryMuscles}
                    />
                ) : musclesLoading ? (
                    <div className="picker-tile-grid-muscle">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <Skeleton
                                key={i}
                                className="h-tile w-full rounded-lg"
                            />
                        ))}
                    </div>
                ) : (
                    <div className="picker-tile-grid-muscle">
                        {muscleOptions.map((name) => (
                            <PickerTile
                                key={name}
                                name={muscle(name)}
                                tabIndex={isExerciseStep ? -1 : 0}
                                onTap={() => onPickMuscle(name)}
                                onLongPress={() => onManageMuscle(name)}
                            />
                        ))}
                        {/* Add a muscle inline (§12.2). */}
                        {!addingMuscle ? (
                            <button
                                type="button"
                                tabIndex={isExerciseStep ? -1 : 0}
                                onClick={onOpenAddMuscle}
                                className="press-95 flex h-tile w-full items-center justify-center rounded-lg border border-dashed border-hairline px-3 text-center text-base text-hint"
                            >
                                {t("picker.addMuscle")}
                            </button>
                        ) : null}
                    </div>
                )}

                {/* GYM-103: "Show Hidden" expander — bottom of muscle panel.
                    Only rendered when there ARE hidden muscles (collapsed
                    by default, hidden entirely when the list is empty). */}
                <ShowHiddenExpander
                    label={t("picker.showHiddenMuscles")}
                    isOpen={showHidden}
                    onToggle={onToggleHidden}
                    isLoading={hiddenLoading}
                    hasHidden={hiddenMuscles.length > 0}
                    tabIndex={isExerciseStep ? -1 : 0}
                >
                    <div className="picker-tile-grid-muscle">
                        {hiddenMuscles.map((m) => (
                            <PickerTile
                                key={m.id}
                                muted
                                name={muscle(m.name)}
                                tabIndex={isExerciseStep ? -1 : 0}
                                isPending={pendingUnhideId === m.id}
                                onLongPress={() => onManageHiddenMuscle(m)}
                            />
                        ))}
                    </div>
                </ShowHiddenExpander>

                {addingMuscle ? (
                    <AddInlineField
                        placeholder={t("picker.newMusclePlaceholder")}
                        actionLabel={t("common.add")}
                        maxLength={MUSCLE_NAME_MAX}
                        pending={createPending}
                        error={createError ? t("picker.addError") : null}
                        onSubmit={onSubmitMuscle}
                        onCancel={onCancelAddMuscle}
                    />
                ) : null}
            </section>
        </div>
    );
}
