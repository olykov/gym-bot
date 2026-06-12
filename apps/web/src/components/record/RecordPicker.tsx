/**
 * Phase A of the record flow — the exercise picker (spec §12.2, GYM-72 v2,
 * GYM-74 slide-nav). Since GYM-127 this file is the ORCHESTRATOR only: all
 * state, derivations and handlers live here; the presentation is composed
 * from <MusclePanel> / <ExercisePanel> (the two slide-track steps),
 * <PickerTile>, <ShowHiddenExpander> and <EmptyNewUserPrompt>.
 *
 * Layout, top to bottom (rendered by the panels):
 *  1. Continue tile — the LAST exercise trained TODAY (derived from
 *     `GET /training/day/{today}`: the group whose set has the highest
 *     training_id). Tap → Phase B. Omitted when nothing was trained today.
 *  2. Muscle TILES (frequency-sorted) → tapping a muscle SLIDES the view LEFT
 *     and the exercise list slides in from the right (GYM-74 horizontal push,
 *     ~200ms ease-out-soft). Top ~6 exercises + "Show all" (§12.9), with the
 *     add-inline + Muscle / + Exercise affordances.
 *
 * The slide track is a horizontal flex of two panels (muscles + exercises),
 * each 100% wide, inside an `overflow:hidden` wrapper. A CSS `translate` on
 * the track animates between the two steps; reduced-motion → instant swap.
 * Non-flickering: both panels stay mounted, only the translate changes.
 *
 * Prefetch (§12.5 perf): on mount (sheet open) warm top-muscles + day/today
 * and the Continue exercise's log-context; on muscle pick prefetch its
 * exercises — so each pick lands instantly.
 *
 * Empty brand-new user (nothing today, empty catalog) → the in-sheet
 * <EmptyNewUserPrompt>; no analytics fan-out on the empty path (§12.6/ARCH §2).
 *
 * GYM-82: long-press (~480ms) on a tile opens the manage sheet (ManageSheet);
 * tap vs long-press disambiguation lives in useTilePressHandlers (used by
 * PickerTile). GYM-103: hidden items render as muted tiles behind the "Show
 * Hidden" expander; long-press offers Unhide.
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useT } from "@/i18n/catalog";
import { ManageSheet } from "./ManageSheet";
import { MusclePanel } from "./MusclePanel";
import { ExercisePanel } from "./ExercisePanel";
import { EmptyNewUserPrompt } from "./EmptyNewUserPrompt";
import { usePickerData } from "./usePickerData";
import {
    useCreateExercise,
    useCreateMuscle,
    useUnhideMuscle,
    useUnhideExercise,
    prefetchMuscleExercises,
} from "@/hooks/useRecord";
import type { PickerStep } from "./RecordSheet";
import type { ChosenExercise } from "./types";
import type { Muscle, Exercise } from "@/api/analytics";
import type { ContinueExercise } from "./MusclePanel";

/** Browse: exercises shown before the "Show all" expand (spec §12.9). */
const BROWSE_VISIBLE = 6;

/** Item info for the manage sheet. */
interface ManageItem {
    id: number;
    name: string;
    kind: "muscle" | "exercise";
    is_mine: boolean;
    muscleName?: string;
    /** Current muscle id — for the GYM-90 move view to exclude the current muscle. */
    muscleId?: number;
}

interface RecordPickerProps {
    /** Today's date (YYYY-MM-DD) — the day/log-context key for the Continue tile. */
    today: string;
    /** Current picker step — controlled by RecordSheet so BackButton can go back. */
    step: PickerStep;
    /** Called when the picker step changes (controlled). */
    onStepChange: (step: PickerStep) => void;
    /**
     * The currently selected muscle — controlled by RecordSheet (GYM-77 #4).
     * Lifting this up means selectedMuscle survives the Phase B round-trip
     * (RecordPicker unmounts/remounts when swapping phases; without this lift,
     * pressing "← Switch exercise" would land on an empty exercise panel because
     * local state would have reset to null).
     */
    selectedMuscle: string | null;
    /** Called when the selected muscle changes (controlled). */
    onMuscleChange: (name: string | null) => void;
    /** Hand the chosen exercise to the controller → swaps to Phase B. */
    onPick: (chosen: ChosenExercise) => void;
    /**
     * GYM-85: called when a create returns resolution=existing so the controller
     * (RecordSheet) can surface the hint in Phase B (SetLogger) after the picker
     * unmounts. Only called for the "existing" resolution; "created" and "unhidden"
     * never call this (silent or no-op).
     */
    onCreateHint: (hint: string) => void;
    /**
     * GYM-139: the exercise most recently logged in this session (muscle+name
     * pair from the last onSetLogged call in RecordSheet). When present it
     * overrides the broken Number(uuid) derivation and guarantees the Continue
     * tile reflects the exercise just logged. Null on fresh opens.
     */
    lastLoggedExercise: ContinueExercise | null;
}

export function RecordPicker({ today, step, onStepChange, selectedMuscle, onMuscleChange, onPick, onCreateHint, lastLoggedExercise }: RecordPickerProps) {
    const { t } = useT();
    const qc = useQueryClient();

    // Read-side queries + derivations (GYM-127: extracted to usePickerData).
    const {
        muscles,
        day,
        hiddenMuscles,
        hiddenExercises,
        fullExercises,
        muscleByName,
        selectedMuscleId,
        ownedExerciseIds,
        exerciseList,
        continueExercise,
        muscleOptions,
    } = usePickerData(today, selectedMuscle, lastLoggedExercise);

    const [showAllExercises, setShowAllExercises] = useState(false);

    const unhideMuscle = useUnhideMuscle();
    const unhideExercise = useUnhideExercise();

    // GYM-103: expander open state (collapsed by default).
    const [showHiddenMuscles, setShowHiddenMuscles] = useState(false);
    const [showHiddenExercises, setShowHiddenExercises] = useState(false);

    // GYM-103: manage sheet for hidden items (Unhide only).
    const [hiddenManageItem, setHiddenManageItem] = useState<ManageItem | null>(null);

    const createMuscle = useCreateMuscle();
    const createExercise = useCreateExercise();

    // Which add-inline field is open (if any).
    const [adding, setAdding] = useState<"muscle" | "exercise" | null>(null);

    /**
     * GYM-85: non-blocking hint shown when POST /muscles or POST /exercises returns
     * resolution=existing (the name matched a visible item — no duplicate created, but
     * the user should know). Cleared whenever the user opens a new add field or navigates.
     * Stays null for resolution=created (normal) and resolution=unhidden (fully silent).
     */
    const [resolveHint, setResolveHint] = useState<string | null>(null);

    // GYM-82: manage sheet state.
    const [manageItem, setManageItem] = useState<ManageItem | null>(null);

    const visibleExercises = showAllExercises
        ? exerciseList
        : exerciseList.slice(0, BROWSE_VISIBLE);
    const hiddenCount = exerciseList.length - visibleExercises.length;

    // Brand-new user: nothing trained today AND no muscles to browse.
    // GYM-103: muscle loading now depends on muscles (not topMuscles — that is
    // used for ordering only; a user with no history can still have muscles).
    const everythingLoaded =
        !day.isLoading && !muscles.isLoading;
    const isEmptyNewUser =
        everythingLoaded && !continueExercise && muscleOptions.length === 0;

    function pickMuscle(name: string): void {
        setShowAllExercises(false);
        setAdding(null);
        setResolveHint(null);
        onMuscleChange(name);
        onStepChange("exercises");
        // GYM-83: warm both top-exercises (for frequency sort) and full catalog.
        const mid = muscleByName.get(name)?.id ?? null;
        prefetchMuscleExercises(qc, name, mid);
    }

    function goBack(): void {
        onMuscleChange(null);
        setShowAllExercises(false);
        setAdding(null);
        setResolveHint(null);
        onStepChange("muscles");
    }

    /**
     * GYM-85: branch on POST /muscles resolution.
     * - created: auto-select and proceed (existing behavior).
     * - unhidden: silently select the returned item (same flow, no message).
     * - existing: show "You already have 'Name'." then proceed with the returned item.
     * Auto-select always uses data.name (the canonical name the backend returned).
     *
     * Note: pickMuscle clears resolveHint so for muscles we set the hint AFTER
     * calling pickMuscle (which navigates to the exercise step) so it shows there.
     */
    function submitMuscle(name: string): void {
        createMuscle.mutate(
            { name },
            {
                onSuccess: (data) => {
                    setAdding(null);
                    const canonicalName = data.name;
                    // Navigate first (pickMuscle resets resolveHint), then set hint.
                    pickMuscle(canonicalName);
                    if (data.resolution === "existing") {
                        setResolveHint(
                            t("picker.alreadyHave", { name: canonicalName }),
                        );
                    }
                },
            },
        );
    }

    /**
     * GYM-85: branch on POST /exercises resolution.
     * - created: auto-select into Phase B (existing behavior).
     * - unhidden: silently select the returned item (no message).
     * - existing: bubble the hint to RecordSheet via onCreateHint (so it survives
     *   RecordPicker unmounting on Phase A→B transition), then proceed.
     * Auto-select always uses data.name (canonical) and data from the returned Exercise.
     */
    function submitExercise(name: string): void {
        const muscleName = selectedMuscle;
        if (!muscleName) return;
        createExercise.mutate(
            { name, muscle_name: muscleName },
            {
                onSuccess: (data) => {
                    setAdding(null);
                    const canonicalName = data.name;
                    if (data.resolution === "existing") {
                        // Bubble to RecordSheet so the hint persists into Phase B
                        // (SetLogger), since onPick immediately unmounts the picker.
                        onCreateHint(
                            t("picker.alreadyHave", { name: canonicalName }),
                        );
                    }
                    // Auto-select into Phase B (§12.2). Uses canonical name from backend.
                    // selectedMuscle is preserved in RecordSheet (GYM-77 #4) so Back
                    // from Phase B lands on the exercise list.
                    onPick({ muscleName, exerciseName: canonicalName });
                },
            },
        );
    }

    // GYM-103: open unhide manage sheet for a hidden muscle tile.
    function openHiddenMuscleManage(m: Muscle): void {
        setHiddenManageItem({
            id: m.id,
            name: m.name,
            kind: "muscle",
            is_mine: false, // hidden items are always global
        });
    }

    // GYM-103: open unhide manage sheet for a hidden exercise tile.
    function openHiddenExerciseManage(ex: Exercise): void {
        setHiddenManageItem({
            id: ex.id,
            name: ex.name,
            kind: "exercise",
            is_mine: false, // hidden items are always global
            muscleName: selectedMuscle ?? undefined,
        });
    }

    // GYM-82: open manage sheet for a muscle tile.
    function openMuscleMange(name: string): void {
        const m = muscleByName.get(name);
        if (!m) return;
        setManageItem({
            id: m.id,
            name: m.name,
            kind: "muscle",
            is_mine: m.is_mine ?? false,
        });
    }

    // GYM-82/GYM-83: open manage sheet for an exercise tile.
    // Tile source is now Exercise[] (full catalog), so id + is_mine are always present.
    function openExerciseManage(ex: Exercise): void {
        setManageItem({
            id: ex.id,
            name: ex.name,
            kind: "exercise",
            is_mine: ex.is_mine ?? false,
            muscleName: selectedMuscle ?? undefined,
            muscleId: selectedMuscleId ?? undefined,
        });
    }

    // Empty new user: front-and-center add-first-exercise prompt (§12.6).
    if (isEmptyNewUser) {
        return (
            <div className="pb-2">
                <EmptyNewUserPrompt
                    selectedMuscle={selectedMuscle}
                    selectedMuscleId={selectedMuscleId}
                    muscleCreatePending={createMuscle.isPending}
                    muscleCreateError={createMuscle.isError}
                    exerciseCreatePending={createExercise.isPending}
                    exerciseCreateError={createExercise.isError}
                    resolveHint={resolveHint}
                    ownedExerciseIds={ownedExerciseIds}
                    onSubmitMuscle={submitMuscle}
                    onSubmitExercise={submitExercise}
                    onPickExercise={(exerciseName) => {
                        setResolveHint(null);
                        onPick({
                            // selectedMuscle is non-null on this branch (the
                            // exercise field only renders after a muscle is set).
                            muscleName: selectedMuscle as string,
                            exerciseName,
                        });
                    }}
                    onCancelExercise={() => {
                        onMuscleChange(null);
                        setResolveHint(null);
                    }}
                />
                {/* Manage sheet (even in empty state, shouldn't be needed but keep consistent). */}
                <ManageSheet
                    open={manageItem !== null}
                    onClose={() => setManageItem(null)}
                    item={manageItem}
                />
            </div>
        );
    }

    // Translate the track: muscles step = translateX(0), exercise step = translateX(-50%).
    // The track is 200% wide; each panel is 50% of the track = 100% of the sheet width.
    const isExerciseStep = step === "exercises";
    const trackStyle: React.CSSProperties = {
        transform: isExerciseStep ? "translateX(-50%)" : "translateX(0)",
        transition: "transform 200ms var(--ease-out-soft)",
        width: "200%",
        display: "flex",
    };

    return (
        // The outer div clips the slide track — overflow:hidden masks the off-screen panel.
        // flex-1 + min-h-0 lets it fill the fixed-height sheet body. overflow-hidden is
        // critical: without it the off-screen panel would be scrollable/visible.
        <div style={{ flex: "1", minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            {/* Slide track: two side-by-side panels, each 50% of the track (= 100% of sheet).
                picker-slide-track class → transition:none under prefers-reduced-motion.
                The track height matches the outer container so each panel can scroll
                independently (overflow-y:auto) without the outer sheet scrolling. */}
            <div className="picker-slide-track" style={{ ...trackStyle, flex: "1", minHeight: 0 }} aria-live="polite">
                <MusclePanel
                    isExerciseStep={isExerciseStep}
                    dayLoading={day.isLoading}
                    continueExercise={continueExercise}
                    onContinue={() => {
                        if (continueExercise) {
                            onPick({
                                muscleName: continueExercise.muscleName,
                                exerciseName: continueExercise.exerciseName,
                            });
                        }
                    }}
                    musclesLoading={muscles.isLoading}
                    musclesError={muscles.isError}
                    onRetryMuscles={() => {
                        void muscles.refetch();
                    }}
                    muscleOptions={muscleOptions}
                    onPickMuscle={pickMuscle}
                    onManageMuscle={openMuscleMange}
                    addingMuscle={adding === "muscle"}
                    onOpenAddMuscle={() => {
                        setAdding("muscle");
                        setResolveHint(null);
                    }}
                    onCancelAddMuscle={() => {
                        setAdding(null);
                        setResolveHint(null);
                    }}
                    createPending={createMuscle.isPending}
                    createError={createMuscle.isError}
                    onSubmitMuscle={submitMuscle}
                    hiddenLoading={hiddenMuscles.isLoading}
                    hiddenMuscles={hiddenMuscles.data ?? []}
                    showHidden={showHiddenMuscles}
                    onToggleHidden={() => setShowHiddenMuscles((v) => !v)}
                    pendingUnhideId={
                        unhideMuscle.isPending
                            ? (hiddenManageItem?.id ?? null)
                            : null
                    }
                    onManageHiddenMuscle={openHiddenMuscleManage}
                />
                <ExercisePanel
                    isExerciseStep={isExerciseStep}
                    selectedMuscle={selectedMuscle}
                    selectedMuscleId={selectedMuscleId}
                    onBack={goBack}
                    exercisesLoading={fullExercises.isLoading}
                    exercisesError={fullExercises.isError}
                    onRetryExercises={() => void fullExercises.refetch()}
                    visibleExercises={visibleExercises}
                    hiddenCount={hiddenCount}
                    onShowAll={() => setShowAllExercises(true)}
                    onPickExercise={(ex) =>
                        onPick({
                            // selectedMuscle is always set on the exercise step.
                            muscleName: selectedMuscle as string,
                            exerciseName: ex.name,
                        })
                    }
                    onManageExercise={openExerciseManage}
                    addingExercise={adding === "exercise"}
                    onOpenAddExercise={() => {
                        setAdding("exercise");
                        setResolveHint(null);
                    }}
                    onCancelAddExercise={() => {
                        setAdding(null);
                        setResolveHint(null);
                    }}
                    createPending={createExercise.isPending}
                    createError={createExercise.isError}
                    onSearchPick={(exerciseName) => {
                        setAdding(null);
                        setResolveHint(null);
                        onPick({
                            muscleName: selectedMuscle as string,
                            exerciseName,
                        });
                    }}
                    onCreateExercise={submitExercise}
                    ownedExerciseIds={ownedExerciseIds}
                    resolveHint={resolveHint}
                    hiddenLoading={hiddenExercises.isLoading}
                    hiddenExercises={hiddenExercises.data ?? []}
                    showHidden={showHiddenExercises}
                    onToggleHidden={() => setShowHiddenExercises((v) => !v)}
                    pendingUnhideId={
                        unhideExercise.isPending
                            ? (hiddenManageItem?.id ?? null)
                            : null
                    }
                    onManageHiddenExercise={openHiddenExerciseManage}
                />
            </div>

            {/* GYM-82: Manage sheet — opened by long-press on any tile. */}
            <ManageSheet
                open={manageItem !== null}
                onClose={() => setManageItem(null)}
                item={manageItem}
            />

            {/* GYM-103: Manage sheet for hidden items — Unhide only. */}
            <ManageSheet
                open={hiddenManageItem !== null}
                onClose={() => setHiddenManageItem(null)}
                item={hiddenManageItem}
                isHiddenItem
                onUnhide={() => {
                    if (!hiddenManageItem) return;
                    if (hiddenManageItem.kind === "muscle") {
                        unhideMuscle.mutate(
                            { muscleId: hiddenManageItem.id },
                            { onSuccess: () => setHiddenManageItem(null) },
                        );
                    } else {
                        unhideExercise.mutate(
                            {
                                exerciseId: hiddenManageItem.id,
                                muscleName: hiddenManageItem.muscleName ?? selectedMuscle ?? "",
                            },
                            { onSuccess: () => setHiddenManageItem(null) },
                        );
                    }
                }}
                isUnhidePending={unhideMuscle.isPending || unhideExercise.isPending}
            />
        </div>
    );
}
