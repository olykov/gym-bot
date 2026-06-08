/**
 * Progress route (spec §10.3) — <MusclePicker> → <ExercisePicker> (dependent
 * chip rows) drive the <ExerciseProgressChart>.
 *
 * Pickers are ordered by the caller's TRAINING FREQUENCY (GYM-62): the muscle
 * row comes from `GET /analytics/top-muscles` and the exercise row from
 * `GET /analytics/top-exercises?muscle&limit=200`, both frequency-desc. The UI
 * renders that order verbatim — no client re-sort, no alphabetical.
 *
 * Non-empty default (GYM-62): on mount the most-frequent muscle is auto-picked,
 * then once its exercises load the most-frequent exercise is auto-picked, so the
 * page opens straight on the By Weight chart of the caller's top exercise — no
 * empty pick-screen. Auto-select runs once and never overrides a manual choice
 * (guarded by a per-muscle ref + the empty-selection check).
 *
 * States are first-class (§10.4): skeleton chips while a row loads, an inline
 * ErrorState + retry on a failed query, and an EmptyState for a brand-new user
 * (no trainings → empty top-muscles, no auto-select, no extra queries) and for a
 * picked exercise with no logged sets. Dependent queries stay disabled until
 * their inputs exist, so the no-data path fires no extra queries.
 */
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SkeletonChart } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ChipRow, type ChipOption } from "@/components/progress/ChipRow";
import type { ProgressMode } from "@/components/progress/ExerciseProgressChart";

// Lazy-load ECharts (~1 MB) so it is excluded from the main bundle and only
// fetched when the Progress tab is opened for the first time (GYM-45).
const ExerciseProgressChart = lazy(
    () => import("@/components/progress/ExerciseProgressChart").then(
        (m) => ({ default: m.ExerciseProgressChart }),
    ),
);
import {
    useExerciseProgress,
    useTopExercises,
    useTopMuscles,
} from "@/hooks/useAnalytics";

const MODE_OPTIONS: { value: ProgressMode; label: string }[] = [
    { value: "weight", label: "By Weight" },
    { value: "set", label: "By Set" },
];

export function Progress() {
    // Pickers are keyed by NAME (the progress endpoint takes muscle/exercise
    // names). The chip `id` is the position in the frequency-ordered row.
    const [muscle, setMuscle] = useState<ChipOption | null>(null);
    const [exercise, setExercise] = useState<ChipOption | null>(null);
    // Default to the overall strength trend (max weight per session). GYM-57.
    const [mode, setMode] = useState<ProgressMode>("weight");

    const muscles = useTopMuscles();
    // Disabled until a muscle is picked (no extra query on the empty path).
    const exercises = useTopExercises(muscle?.label ?? null);
    // Disabled until both names exist.
    const progress = useExerciseProgress(
        muscle?.label ?? null,
        exercise?.label ?? null,
    );

    // Frequency order is authoritative — index is the chip id, name the label.
    const muscleOptions: ChipOption[] = useMemo(
        () => (muscles.data ?? []).map((m, i) => ({ id: i, label: m.name })),
        [muscles.data],
    );
    const exerciseOptions: ChipOption[] = useMemo(
        () => (exercises.data ?? []).map((e, i) => ({ id: i, label: e.name })),
        [exercises.data],
    );

    // Auto-select the top muscle once, only while nothing is picked. A manual
    // pick (or a re-render after one) is never clobbered.
    const didDefaultMuscle = useRef(false);
    useEffect(() => {
        if (didDefaultMuscle.current || muscle) return;
        const top = muscleOptions[0];
        if (!top) return;
        didDefaultMuscle.current = true;
        setMuscle(top);
    }, [muscleOptions, muscle]);

    // Auto-select the top exercise of the just-defaulted muscle, once per muscle
    // and only while no exercise is picked — so a manual exercise pick stands.
    const defaultedExerciseFor = useRef<string | null>(null);
    useEffect(() => {
        if (!muscle || exercise) return;
        if (defaultedExerciseFor.current === muscle.label) return;
        const top = exerciseOptions[0];
        if (!top) return;
        defaultedExerciseFor.current = muscle.label;
        setExercise(top);
    }, [muscle, exercise, exerciseOptions]);

    function pickMuscle(opt: ChipOption): void {
        setMuscle(opt);
        setExercise(null); // reset the dependent pick
        // Let the new muscle's top exercise auto-select once its row loads.
        defaultedExerciseFor.current = null;
    }

    if (muscles.isError) {
        return <ErrorState onRetry={() => muscles.refetch()} />;
    }

    // Brand-new user: no trainings → no muscles → keep the empty state, fire no
    // dependent queries, run no auto-select (the effects no-op on []).
    if (!muscles.isLoading && muscleOptions.length === 0) {
        return (
            <EmptyState
                title="No trainings yet"
                subtitle="Log a set in the bot and your progress shows up here."
            />
        );
    }

    return (
        <>
            <Card>
                <SegmentedControl
                    ariaLabel="Progress view"
                    options={MODE_OPTIONS}
                    value={mode}
                    onChange={setMode}
                />
                <div className="mt-4">
                    <ChipRow
                        label="Muscle"
                        options={muscleOptions}
                        selectedId={muscle?.id ?? null}
                        onSelect={pickMuscle}
                        loading={muscles.isLoading}
                    />
                </div>
                {muscle ? (
                    <div className="mt-4">
                        <ChipRow
                            label="Exercise"
                            options={exerciseOptions}
                            selectedId={exercise?.id ?? null}
                            onSelect={setExercise}
                            loading={exercises.isLoading}
                        />
                    </div>
                ) : null}
            </Card>

            <ChartArea
                muscle={muscle}
                exercise={exercise}
                progress={progress}
                mode={mode}
            />
        </>
    );
}

/** The result region under the pickers: empty → skeleton → error → chart/empty. */
function ChartArea({
    muscle,
    exercise,
    progress,
    mode,
}: {
    muscle: ChipOption | null;
    exercise: ChipOption | null;
    progress: ReturnType<typeof useExerciseProgress>;
    mode: ProgressMode;
}) {
    // No selection resolved yet (auto-select in flight) — a skeleton, not an
    // empty screen, so the page never flashes a blank pick state on mount.
    if (!muscle || !exercise) {
        return <SkeletonChart />;
    }

    if (progress.isLoading) return <SkeletonChart />;
    if (progress.isError) {
        return <ErrorState onRetry={() => progress.refetch()} />;
    }

    const series = progress.data?.series ?? [];
    const hasPoints = series.some((s) => s.points.length > 0);
    if (!hasPoints) {
        return (
            <EmptyState
                title="No data yet"
                subtitle={`No logged sets for ${exercise.label}. Record a set in the bot to start the chart.`}
            />
        );
    }

    return (
        <Suspense fallback={<SkeletonChart />}>
            <ExerciseProgressChart
                title={exercise.label}
                progress={progress.data!}
                mode={mode}
            />
        </Suspense>
    );
}
