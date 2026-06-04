/**
 * Progress route (spec §10.3) — <MusclePicker> → <ExercisePicker> (dependent
 * chip rows) drive the <ExerciseProgressChart>.
 *
 * States are first-class (§10.4): skeleton chips while the catalog loads, an
 * inline ErrorState + retry on any failed query, an EmptyState before a pick and
 * for an exercise with no logged sets. Dependent queries stay disabled until
 * their inputs exist, so the no-selection path fires no extra queries.
 */
import { useMemo, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SkeletonChart } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { ChipRow, type ChipOption } from "@/components/progress/ChipRow";
import {
    ExerciseProgressChart,
    type ProgressMode,
} from "@/components/progress/ExerciseProgressChart";
import {
    useExerciseProgress,
    useExercises,
    useMuscles,
} from "@/hooks/useAnalytics";

const MODE_OPTIONS: { value: ProgressMode; label: string }[] = [
    { value: "weight", label: "By Weight" },
    { value: "set", label: "By Set" },
];

export function Progress() {
    const [muscle, setMuscle] = useState<ChipOption | null>(null);
    const [exercise, setExercise] = useState<ChipOption | null>(null);
    // Default to the overall strength trend (max weight per session). GYM-57.
    const [mode, setMode] = useState<ProgressMode>("weight");

    const muscles = useMuscles();
    // Disabled until a muscle is picked (no extra query on the empty path).
    const exercises = useExercises(muscle?.id ?? null);
    // Disabled until both names exist.
    const progress = useExerciseProgress(
        muscle?.label ?? null,
        exercise?.label ?? null,
    );

    const muscleOptions: ChipOption[] = useMemo(
        () => (muscles.data ?? []).map((m) => ({ id: m.id, label: m.name })),
        [muscles.data],
    );
    const exerciseOptions: ChipOption[] = useMemo(
        () => (exercises.data ?? []).map((e) => ({ id: e.id, label: e.name })),
        [exercises.data],
    );

    function pickMuscle(opt: ChipOption): void {
        setMuscle(opt);
        setExercise(null); // reset the dependent pick
    }

    if (muscles.isError) {
        return <ErrorState onRetry={() => muscles.refetch()} />;
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
    // No selection yet — guidance, no query fired.
    if (!muscle || !exercise) {
        return (
            <EmptyState
                title="Pick an exercise"
                subtitle="Choose a muscle and exercise to see your weight and reps over time."
            />
        );
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
        <ExerciseProgressChart
            title={exercise.label}
            progress={progress.data!}
            mode={mode}
        />
    );
}
