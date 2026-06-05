/**
 * Phase A of the record flow — the exercise picker (spec §12.2, GYM-72 v2,
 * GYM-74 slide-nav).
 *
 * Layout, top to bottom:
 *  1. Continue tile — the LAST exercise trained TODAY (derived from
 *     `GET /training/day/{today}`: the exercise group whose set has the highest
 *     training_id, i.e. the most recently logged). Tap → Phase B. Omitted
 *     entirely when nothing was trained today.
 *  2. A very light, fading hairline divider below the Continue tile (only shown
 *     with the tile) — a whisper of separation, not a hard cut.
 *  3. Muscle TILES (frequency-sorted top-muscles, then the rest of /muscles) →
 *     tapping a muscle SLIDES the view LEFT and the exercise list SLIDES IN
 *     from the right (GYM-74 horizontal push, ~200ms ease-out-soft). The Back
 *     affordance (and the Telegram BackButton, wired in RecordSheet) slides back.
 *     Exercise tiles appear on the right panel in the same tile format. Keep
 *     the add-inline + Muscle / + Exercise. Top ~6 + "Show all" (§12.9).
 *
 * The slide track is a horizontal flex of two panels (muscles + exercises),
 * each 100% wide, inside an `overflow:hidden` wrapper. A CSS `translate` on the
 * track animates between the two steps. Reduced-motion → instant swap (no
 * transition). Non-flickering: both panels stay mounted, only translate changes.
 *
 * Muscle tiles use an auto-fit grid (minmax(100px, 1fr)) so long names and
 * custom muscles lay out correctly without hardcoded column counts. Tile minimum
 * height is 64px (bigger than the old 52px, per GYM-74). Exercise tiles share
 * the same tile language.
 *
 * Prefetch (§12.5 perf): on mount (sheet open) warm top-muscles + day/today and
 * the Continue exercise's log-context; on muscle pick prefetch its exercises —
 * so each pick lands instantly.
 *
 * Empty brand-new user (nothing today, empty catalog) → an in-sheet
 * "ADD YOUR FIRST EXERCISE" prompt with the add-inline field; no analytics
 * fan-out on the empty path (§12.6 / ARCH §2).
 */
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MUSCLE_NAME_MAX, EXERCISE_NAME_MAX } from "@/validation";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { AddInlineField } from "./AddInlineField";
import { useMuscles, useTopMuscles, useTopExercises } from "@/hooks/useAnalytics";
import { useTrainingDay } from "@/hooks/useTraining";
import {
    useCreateExercise,
    useCreateMuscle,
    prefetchPickerReads,
    prefetchMuscleExercises,
    prefetchLogContext,
} from "@/hooks/useRecord";
import type { PickerStep } from "./RecordSheet";
import type { ChosenExercise } from "./types";

/** Browse: exercises shown before the "Show all" expand (spec §12.9). */
const BROWSE_VISIBLE = 6;

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
}

/** The last exercise trained today: the group whose set has the highest id. */
interface ContinueExercise {
    muscleName: string;
    exerciseName: string;
}

export function RecordPicker({ today, step, onStepChange, selectedMuscle, onMuscleChange, onPick }: RecordPickerProps) {
    const qc = useQueryClient();
    const topMuscles = useTopMuscles();
    const muscles = useMuscles();
    const day = useTrainingDay(today);

    const [showAllExercises, setShowAllExercises] = useState(false);
    const exercises = useTopExercises(selectedMuscle);

    const createMuscle = useCreateMuscle();
    const createExercise = useCreateExercise();

    // Which add-inline field is open (if any).
    const [adding, setAdding] = useState<"muscle" | "exercise" | null>(null);

    // Warm the picker reads + the Continue exercise's log-context on open (§12.5).
    useEffect(() => {
        prefetchPickerReads(qc, today);
    }, [qc, today]);

    // Continue = the exercise group whose set has the highest training_id
    // (the most recently logged today). training_id is a serial id, so the
    // largest value is the latest insert. Falls back to string compare.
    const continueExercise: ContinueExercise | null = useMemo(() => {
        const exs = day.data?.exercises ?? [];
        if (exs.length === 0) return null;
        let best: ContinueExercise | null = null;
        let bestKey = -Infinity;
        for (const ex of exs) {
            for (const s of ex.sets) {
                const k = Number(s.training_id);
                const key = Number.isFinite(k) ? k : -Infinity;
                if (key > bestKey) {
                    bestKey = key;
                    best = {
                        muscleName: ex.muscle_name,
                        exerciseName: ex.exercise_name,
                    };
                }
            }
        }
        // No finite id anywhere → fall back to first appearance (alpha order).
        if (!best && exs[0]) {
            best = {
                muscleName: exs[0].muscle_name,
                exerciseName: exs[0].exercise_name,
            };
        }
        return best;
    }, [day.data]);

    // Prefetch the Continue exercise's log-context so tapping it is instant.
    useEffect(() => {
        if (continueExercise) {
            prefetchLogContext(
                qc,
                continueExercise.muscleName,
                continueExercise.exerciseName,
                today,
            );
        }
    }, [qc, continueExercise, today]);

    // Merge top-muscles (frequency order) with the rest of the catalog, so a
    // user with private muscles never-trained can still browse them.
    const muscleOptions = useMemo(() => {
        const seen = new Set<string>();
        const out: string[] = [];
        for (const m of topMuscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push(m.name);
        }
        for (const m of muscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push(m.name);
        }
        return out;
    }, [topMuscles.data, muscles.data]);

    const exerciseList = exercises.data ?? [];
    const visibleExercises = showAllExercises
        ? exerciseList
        : exerciseList.slice(0, BROWSE_VISIBLE);
    const hiddenCount = exerciseList.length - visibleExercises.length;

    // Brand-new user: nothing trained today AND no muscles to browse.
    const everythingLoaded =
        !day.isLoading && !topMuscles.isLoading && !muscles.isLoading;
    const isEmptyNewUser =
        everythingLoaded && !continueExercise && muscleOptions.length === 0;

    function pickMuscle(name: string): void {
        setShowAllExercises(false);
        setAdding(null);
        onMuscleChange(name);
        onStepChange("exercises");
        prefetchMuscleExercises(qc, name);
    }

    function goBack(): void {
        onMuscleChange(null);
        setShowAllExercises(false);
        setAdding(null);
        onStepChange("muscles");
    }

    function submitMuscle(name: string): void {
        createMuscle.mutate(
            { name },
            {
                onSuccess: () => {
                    setAdding(null);
                    pickMuscle(name);
                },
            },
        );
    }

    function submitExercise(name: string): void {
        const muscleName = selectedMuscle;
        if (!muscleName) return;
        createExercise.mutate(
            { name, muscle_name: muscleName },
            {
                onSuccess: () => {
                    setAdding(null);
                    // Auto-select the new exercise into Phase B (§12.2). No
                    // history yet → cold pre-fill stays empty until valid.
                    // selectedMuscle is preserved in RecordSheet (GYM-77 #4)
                    // so Back from Phase B will land on the exercise list.
                    onPick({ muscleName, exerciseName: name });
                },
            },
        );
    }

    // Empty new user: front-and-center add-first-exercise prompt (§12.6).
    if (isEmptyNewUser) {
        return (
            <div className="pb-2">
                <h2 className="font-display text-title text-text">RECORD</h2>
                <div className="mt-6">
                    <EmptyState
                        title="ADD YOUR FIRST EXERCISE"
                        subtitle="Name a muscle, then an exercise under it — you'll log your first set right after."
                    />
                    <div className="mt-2 space-y-3">
                        {!selectedMuscle ? (
                            <AddInlineField
                                placeholder="Muscle (e.g. Chest)"
                                actionLabel="Add"
                                maxLength={MUSCLE_NAME_MAX}
                                pending={createMuscle.isPending}
                                error={
                                    createMuscle.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitMuscle}
                            />
                        ) : (
                            <AddInlineField
                                placeholder={`Exercise in ${selectedMuscle}`}
                                actionLabel="Add"
                                maxLength={EXERCISE_NAME_MAX}
                                pending={createExercise.isPending}
                                error={
                                    createExercise.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitExercise}
                                onCancel={() => onMuscleChange(null)}
                            />
                        )}
                    </div>
                </div>
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
                {/* ── PANEL 1: Muscle step ─────────────────────────────────── */}
                <div
                    className="space-y-4"
                    aria-hidden={isExerciseStep}
                    style={{ width: "50%", minWidth: 0, overflowY: "auto", height: "100%", paddingBottom: "8px", paddingRight: "4px" }}
                >
                    <h2 className="font-display text-title text-text">RECORD</h2>

                    {/* Continue today tile (§12.2 v2). */}
                    {day.isLoading ? (
                        <Skeleton className="h-[60px] w-full rounded-lg" />
                    ) : continueExercise ? (
                        <>
                            <button
                                type="button"
                                tabIndex={isExerciseStep ? -1 : 0}
                                onClick={() =>
                                    onPick({
                                        muscleName: continueExercise.muscleName,
                                        exerciseName: continueExercise.exerciseName,
                                    })
                                }
                                className="press-95 flex min-h-[60px] w-full items-center justify-between gap-3 rounded-lg border border-hairline bg-secondary-bg px-4 py-3 text-left"
                            >
                                <span className="min-w-0">
                                    <span className="block text-label uppercase tracking-wide text-hint">
                                        Continue today
                                    </span>
                                    <span className="mt-0.5 block truncate text-base font-semibold text-text">
                                        {continueExercise.exerciseName}
                                    </span>
                                    <span className="block truncate text-label text-hint">
                                        {continueExercise.muscleName}
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
                            Muscle
                        </div>

                        {topMuscles.isError && muscles.isError ? (
                            <ErrorState
                                message="Couldn't load muscles."
                                onRetry={() => {
                                    void topMuscles.refetch();
                                    void muscles.refetch();
                                }}
                            />
                        ) : topMuscles.isLoading && muscles.isLoading ? (
                            <div className="picker-tile-grid-muscle">
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <Skeleton
                                        key={i}
                                        className="w-full rounded-lg"
                                        style={{ height: "88px" }}
                                    />
                                ))}
                            </div>
                        ) : (
                            <div className="picker-tile-grid-muscle">
                                {muscleOptions.map((name) => (
                                    <button
                                        key={name}
                                        type="button"
                                        tabIndex={isExerciseStep ? -1 : 0}
                                        onClick={() => pickMuscle(name)}
                                        title={name}
                                        className="press-95 flex w-full items-center justify-center rounded-lg border border-hairline bg-secondary-bg px-3 text-center text-base text-text"
                                        style={{ height: "88px" }}
                                    >
                                        <span className="tile-name">{name}</span>
                                    </button>
                                ))}
                                {/* Add a muscle inline (§12.2). */}
                                {adding !== "muscle" ? (
                                    <button
                                        type="button"
                                        tabIndex={isExerciseStep ? -1 : 0}
                                        onClick={() => setAdding("muscle")}
                                        className="press-95 flex w-full items-center justify-center rounded-lg border border-dashed border-hairline px-3 text-center text-base text-hint"
                                        style={{ height: "88px" }}
                                    >
                                        + Muscle
                                    </button>
                                ) : null}
                            </div>
                        )}

                        {adding === "muscle" ? (
                            <AddInlineField
                                placeholder="New muscle name"
                                actionLabel="Add"
                                maxLength={MUSCLE_NAME_MAX}
                                pending={createMuscle.isPending}
                                error={
                                    createMuscle.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitMuscle}
                                onCancel={() => setAdding(null)}
                            />
                        ) : null}
                    </section>
                </div>

                {/* ── PANEL 2: Exercise step ───────────────────────────────── */}
                <div
                    className="space-y-4"
                    aria-hidden={!isExerciseStep}
                    style={{ width: "50%", minWidth: 0, overflowY: "auto", height: "100%", paddingBottom: "8px", paddingRight: "4px" }}
                >
                    {/* Back to muscles control (in-body; mirrors Phase B's "← Switch exercise"). */}
                    <button
                        type="button"
                        tabIndex={isExerciseStep ? 0 : -1}
                        onClick={goBack}
                        className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
                    >
                        ← {selectedMuscle ?? "Muscles"}
                    </button>

                    <h2 className="font-display text-title text-text">
                        {selectedMuscle ?? ""}
                    </h2>

                    {/* Exercise tiles — 2-column grid, fixed height, line-clamp (GYM-77 #1/#3). */}
                    {exercises.isLoading ? (
                        <div className="picker-tile-grid-exercise">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <Skeleton
                                    key={i}
                                    className="w-full rounded-lg"
                                    style={{ height: "88px" }}
                                />
                            ))}
                        </div>
                    ) : exercises.isError ? (
                        <ErrorState
                            message="Couldn't load exercises."
                            onRetry={() => void exercises.refetch()}
                        />
                    ) : (
                        <div className="picker-tile-grid-exercise">
                            {visibleExercises.map((ex) => (
                                <button
                                    key={ex.name}
                                    type="button"
                                    tabIndex={isExerciseStep ? 0 : -1}
                                    onClick={() =>
                                        onPick({
                                            muscleName: selectedMuscle!,
                                            exerciseName: ex.name,
                                        })
                                    }
                                    title={ex.name}
                                    className="press-95 flex w-full items-center justify-center rounded-lg border border-hairline bg-secondary-bg px-3 text-center text-base text-text"
                                    style={{ height: "88px" }}
                                >
                                    <span className="tile-name">{ex.name}</span>
                                </button>
                            ))}
                            {hiddenCount > 0 ? (
                                <button
                                    type="button"
                                    tabIndex={isExerciseStep ? 0 : -1}
                                    onClick={() => setShowAllExercises(true)}
                                    className="press-95 flex w-full items-center justify-center rounded-lg bg-accent-weak px-3 text-center text-base font-semibold text-accent"
                                    style={{ height: "88px" }}
                                >
                                    Show all ({hiddenCount})
                                </button>
                            ) : null}
                        </div>
                    )}

                    {/* Add an exercise inline (§12.2). */}
                    {adding === "exercise" ? (
                        <AddInlineField
                            placeholder={`New exercise in ${selectedMuscle ?? ""}`}
                            actionLabel="Add"
                            maxLength={EXERCISE_NAME_MAX}
                            pending={createExercise.isPending}
                            error={
                                createExercise.isError
                                    ? "Couldn't add that — try again."
                                    : null
                            }
                            onSubmit={submitExercise}
                            onCancel={() => setAdding(null)}
                        />
                    ) : (
                        <button
                            type="button"
                            tabIndex={isExerciseStep ? 0 : -1}
                            onClick={() => setAdding("exercise")}
                            className="press-95 min-h-[44px] rounded-full border border-dashed border-hairline px-4 text-base text-hint"
                        >
                            + Exercise
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
