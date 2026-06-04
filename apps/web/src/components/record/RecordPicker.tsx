/**
 * Phase A of the record flow — the exercise picker (spec §12.2, GYM-72 v2).
 *
 * Layout, top to bottom:
 *  1. Continue tile — the LAST exercise trained TODAY (derived from
 *     `GET /training/day/{today}`: the exercise group whose set has the highest
 *     training_id, i.e. the most recently logged). Tap → Phase B. Omitted
 *     entirely when nothing was trained today.
 *  2. A very light, fading hairline divider below the Continue tile (only shown
 *     with the tile) — a whisper of separation, not a hard cut.
 *  3. Muscle TILES (frequency-sorted top-muscles, then the rest of /muscles) →
 *     on pick, exercise TILES in the SAME tile format (top ~6 + "Show all"
 *     client-side expand, §12.9). Keep the add-inline + Muscle / + Exercise.
 *
 * The old 8-item "Recent" fast lane is removed (operator feedback): just-logged
 * exercises aren't what you want next.
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
import type { ChosenExercise } from "./types";

/** Browse: exercises shown before the "Show all" expand (spec §12.9). */
const BROWSE_VISIBLE = 6;

interface RecordPickerProps {
    /** Today's date (YYYY-MM-DD) — the day/log-context key for the Continue tile. */
    today: string;
    /** Hand the chosen exercise to the controller → swaps to Phase B. */
    onPick: (chosen: ChosenExercise) => void;
}

/** The last exercise trained today: the group whose set has the highest id. */
interface ContinueExercise {
    muscleName: string;
    exerciseName: string;
}

export function RecordPicker({ today, onPick }: RecordPickerProps) {
    const qc = useQueryClient();
    const topMuscles = useTopMuscles();
    const muscles = useMuscles();
    const day = useTrainingDay(today);

    const [selectedMuscle, setSelectedMuscle] = useState<string | null>(null);
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
        const next = name === selectedMuscle ? null : name;
        setSelectedMuscle(next);
        if (next) prefetchMuscleExercises(qc, next);
    }

    function submitMuscle(name: string): void {
        createMuscle.mutate(
            { name },
            {
                onSuccess: () => {
                    setSelectedMuscle(name);
                    setAdding(null);
                    setShowAllExercises(false);
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
                                pending={createExercise.isPending}
                                error={
                                    createExercise.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitExercise}
                                onCancel={() => setSelectedMuscle(null)}
                            />
                        )}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 pb-2">
            <h2 className="font-display text-title text-text">RECORD</h2>

            {/* Continue today — the last exercise trained today (§12.2 v2). */}
            {day.isLoading ? (
                <Skeleton className="h-[60px] w-full rounded-lg" />
            ) : continueExercise ? (
                <>
                    <button
                        type="button"
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

                    {/* Very light, fading hairline — a whisper, not a hard cut
                        (operator: "совсем лёгкий, ненавязчивый"). Inset + masked
                        to transparent at both ends; only shown with Continue. */}
                    <div
                        aria-hidden
                        className="record-divider-faint mx-auto h-px w-2/3"
                    />
                </>
            ) : null}

            {/* Muscle tiles → exercise tiles (§12.2 v2 / §12.9). */}
            <section className="space-y-4">
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
                    <div className="flex flex-wrap gap-2">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <Skeleton
                                key={i}
                                className="h-[52px] w-28 rounded-lg"
                            />
                        ))}
                    </div>
                ) : (
                    <div className="-mx-1 flex flex-wrap gap-2 px-1">
                        {muscleOptions.map((name) => {
                            const active = name === selectedMuscle;
                            return (
                                <button
                                    key={name}
                                    type="button"
                                    onClick={() => pickMuscle(name)}
                                    aria-pressed={active}
                                    className={`press-95 flex min-h-[52px] items-center rounded-lg px-4 text-base transition-colors ${
                                        active
                                            ? "border border-transparent bg-accent-weak font-semibold text-accent"
                                            : "border border-hairline bg-secondary-bg text-text"
                                    }`}
                                >
                                    {name}
                                </button>
                            );
                        })}
                        {/* Add a muscle inline (§12.2). */}
                        {adding === "muscle" ? null : (
                            <button
                                type="button"
                                onClick={() => setAdding("muscle")}
                                className="press-95 flex min-h-[52px] items-center rounded-lg border border-dashed border-hairline px-4 text-base text-hint"
                            >
                                + Muscle
                            </button>
                        )}
                    </div>
                )}

                {adding === "muscle" ? (
                    <AddInlineField
                        placeholder="New muscle name"
                        actionLabel="Add"
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

                {/* Exercises of the selected muscle: top ~6 + "Show all" (§12.9). */}
                {selectedMuscle ? (
                    <div className="space-y-3">
                        <div className="text-label uppercase tracking-wide text-hint">
                            {selectedMuscle}
                        </div>
                        {exercises.isLoading ? (
                            <div className="flex flex-wrap gap-2">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <Skeleton
                                        key={i}
                                        className="h-[52px] w-28 rounded-lg"
                                    />
                                ))}
                            </div>
                        ) : exercises.isError ? (
                            <ErrorState
                                message="Couldn't load exercises."
                                onRetry={() => void exercises.refetch()}
                            />
                        ) : (
                            <div className="-mx-1 flex flex-wrap gap-2 px-1">
                                {visibleExercises.map((ex) => (
                                    <button
                                        key={ex.name}
                                        type="button"
                                        onClick={() =>
                                            onPick({
                                                muscleName: selectedMuscle,
                                                exerciseName: ex.name,
                                            })
                                        }
                                        className="press-95 flex min-h-[52px] items-center rounded-lg border border-hairline bg-secondary-bg px-4 text-base text-text"
                                    >
                                        {ex.name}
                                    </button>
                                ))}
                                {hiddenCount > 0 ? (
                                    <button
                                        type="button"
                                        onClick={() => setShowAllExercises(true)}
                                        className="press-95 flex min-h-[52px] items-center rounded-lg bg-accent-weak px-4 text-base font-semibold text-accent"
                                    >
                                        Show all ({hiddenCount})
                                    </button>
                                ) : null}
                            </div>
                        )}

                        {/* Add an exercise inline (§12.2). */}
                        {adding === "exercise" ? (
                            <AddInlineField
                                placeholder={`New exercise in ${selectedMuscle}`}
                                actionLabel="Add"
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
                                onClick={() => setAdding("exercise")}
                                className="press-95 min-h-[44px] rounded-full border border-dashed border-hairline px-4 text-base text-hint"
                            >
                                + Exercise
                            </button>
                        )}
                    </div>
                ) : null}
            </section>
        </div>
    );
}
