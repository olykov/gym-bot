/**
 * Phase A of the record flow — the exercise picker (spec §12.2). Goal: get the
 * user onto an exercise in ONE tap on the hot path.
 *
 * Layout, in priority order:
 *  1. Fast lane — `recent-exercises` 1-tap chips (cross-muscle, newest first),
 *     each carrying the last working set so Phase B pre-fills instantly.
 *  2. Browse fallback — a muscle <ChipRow> (top-muscles then /muscles); picking
 *     a muscle reveals its exercises frequency-sorted, rendered top ~6 + a
 *     "Show all" chip that expands the rest client-side (§12.9).
 *  3. Add inline — `+ Muscle` / `+ Exercise` open an in-sheet text field;
 *     create + optimistic insert + auto-select into Phase B.
 *
 * Empty brand-new user (no recent, empty catalog) → an in-sheet
 * "ADD YOUR FIRST EXERCISE" prompt with the add-inline field; no analytics
 * fan-out on the empty path (§12.6 / ARCH §2).
 */
import { useMemo, useState } from "react";
import { ChipRow, type ChipOption } from "@/components/progress/ChipRow";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { AddInlineField } from "./AddInlineField";
import { useMuscles, useTopMuscles, useTopExercises } from "@/hooks/useAnalytics";
import {
    useRecentExercises,
    useCreateExercise,
    useCreateMuscle,
} from "@/hooks/useRecord";
import type { ChosenExercise } from "./types";

/** Browse: exercises shown before the "Show all" expand (spec §12.9). */
const BROWSE_VISIBLE = 6;

interface RecordPickerProps {
    /** Hand the chosen exercise to the controller → swaps to Phase B. */
    onPick: (chosen: ChosenExercise) => void;
}

export function RecordPicker({ onPick }: RecordPickerProps) {
    const recent = useRecentExercises(true);
    const topMuscles = useTopMuscles();
    const muscles = useMuscles();

    const [selectedMuscle, setSelectedMuscle] = useState<string | null>(null);
    const [showAllExercises, setShowAllExercises] = useState(false);
    const exercises = useTopExercises(selectedMuscle);

    const createMuscle = useCreateMuscle();
    const createExercise = useCreateExercise();

    // Which add-inline field is open (if any).
    const [adding, setAdding] = useState<"muscle" | "exercise" | null>(null);

    // Merge top-muscles (frequency order) with the rest of the catalog, so a
    // user with private muscles never-trained can still browse them.
    const muscleOptions: ChipOption[] = useMemo(() => {
        const seen = new Set<string>();
        const out: ChipOption[] = [];
        let i = 0;
        for (const m of topMuscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push({ id: i++, label: m.name });
        }
        for (const m of muscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push({ id: i++, label: m.name });
        }
        return out;
    }, [topMuscles.data, muscles.data]);

    const exerciseList = exercises.data ?? [];
    const visibleExercises = showAllExercises
        ? exerciseList
        : exerciseList.slice(0, BROWSE_VISIBLE);
    const hiddenCount = exerciseList.length - visibleExercises.length;

    // Brand-new user: no recent exercises AND no muscles to browse.
    const everythingLoaded =
        !recent.isLoading && !topMuscles.isLoading && !muscles.isLoading;
    const isEmptyNewUser =
        everythingLoaded &&
        (recent.data?.length ?? 0) === 0 &&
        muscleOptions.length === 0;

    function pickMuscle(option: ChipOption): void {
        setShowAllExercises(false);
        setAdding(null);
        setSelectedMuscle(
            option.label === selectedMuscle ? null : option.label,
        );
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
                    // recent row yet → cold pre-fill falls back to PR/empty.
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

            {/* Fast lane — recent-exercises 1-tap chips (§12.2). */}
            <section>
                <div className="mb-2 text-label uppercase tracking-wide text-hint">
                    Recent
                </div>
                {recent.isLoading ? (
                    <div className="flex gap-2 overflow-hidden">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <Skeleton
                                key={i}
                                className="h-[52px] w-28 shrink-0 rounded-lg"
                            />
                        ))}
                    </div>
                ) : recent.isError ? (
                    // Degrade, don't block: the browse path below still works.
                    <p className="text-label text-hint">
                        Couldn't load recents — browse below.
                    </p>
                ) : (recent.data?.length ?? 0) === 0 ? (
                    <p className="text-label text-hint">
                        No recents yet — browse below.
                    </p>
                ) : (
                    <div className="-mx-1 flex flex-wrap gap-2 px-1">
                        {recent.data?.map((ex) => (
                            <button
                                key={`${ex.muscle_name}/${ex.exercise_name}`}
                                type="button"
                                onClick={() =>
                                    onPick({
                                        muscleName: ex.muscle_name,
                                        exerciseName: ex.exercise_name,
                                        lastWeight: ex.last_weight,
                                        lastReps: ex.last_reps,
                                    })
                                }
                                className="press-95 flex min-h-[52px] flex-col items-start justify-center rounded-lg border border-hairline bg-secondary-bg px-4 py-2 text-left"
                            >
                                <span className="text-base font-semibold text-text">
                                    {ex.exercise_name}
                                </span>
                                <span className="text-label text-hint">
                                    {ex.muscle_name}
                                </span>
                            </button>
                        ))}
                    </div>
                )}
            </section>

            {/* Browse fallback — muscle row → exercise row (§12.2 / §12.9). */}
            <section className="space-y-4">
                {topMuscles.isError && muscles.isError ? (
                    <ErrorState
                        message="Couldn't load muscles."
                        onRetry={() => {
                            void topMuscles.refetch();
                            void muscles.refetch();
                        }}
                    />
                ) : (
                    <ChipRow
                        label="Browse by muscle"
                        options={muscleOptions}
                        selectedId={
                            muscleOptions.find((o) => o.label === selectedMuscle)
                                ?.id ?? null
                        }
                        onSelect={pickMuscle}
                        loading={topMuscles.isLoading && muscles.isLoading}
                    />
                )}

                {/* Add a muscle inline (§12.2). */}
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
                ) : (
                    <button
                        type="button"
                        onClick={() => setAdding("muscle")}
                        className="press-95 min-h-[44px] rounded-full border border-dashed border-hairline px-4 text-base text-hint"
                    >
                        + Muscle
                    </button>
                )}

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
                                        className="h-[44px] w-24 rounded-full"
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
                                        className="press-95 flex min-h-[44px] items-center whitespace-nowrap rounded-full border border-hairline px-4 text-base text-text"
                                    >
                                        {ex.name}
                                    </button>
                                ))}
                                {hiddenCount > 0 ? (
                                    <button
                                        type="button"
                                        onClick={() => setShowAllExercises(true)}
                                        className="press-95 flex min-h-[44px] items-center whitespace-nowrap rounded-full bg-accent-weak px-4 text-base font-semibold text-accent"
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
