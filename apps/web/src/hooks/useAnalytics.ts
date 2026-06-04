/**
 * TanStack Query hooks for the analytics + catalog reads (spec §1, §10.4).
 *
 * Every API read in the MVP screens goes through one of these so loading/error/
 * cache are uniform: a skeleton on `isLoading`, an ErrorState on `isError`, and
 * a sane TTL so we never re-fetch on every mount. Dependent queries (exercises,
 * progress) stay disabled until their inputs exist — so the empty path never
 * fires extra queries (ARCH §2 "empty path is the most expensive" lesson).
 */
import { useQuery } from "@tanstack/react-query";
import {
    fetchActivity,
    fetchExerciseProgress,
    fetchExercises,
    fetchMuscles,
    fetchSummary,
    fetchTopExercises,
    fetchTopMuscles,
    type ActivityDay,
    type AnalyticsSummary,
    type Exercise,
    type ExerciseProgress,
    type Muscle,
    type TopExercise,
    type TopMuscle,
} from "@/api/analytics";

/** Pull-all sentinel for the exercise picker (every exercise of a muscle). */
const TOP_EXERCISES_LIMIT = 200;

/** Dashboard summary numbers. */
export function useSummary() {
    return useQuery<AnalyticsSummary>({
        queryKey: ["analytics", "summary"],
        queryFn: ({ signal }) => fetchSummary(signal),
    });
}

/** Activity grid for a date window (the 26-week MVP window, see ActivityGrid). */
export function useActivity(from: string, to: string) {
    return useQuery<ActivityDay[]>({
        queryKey: ["analytics", "activity", from, to],
        queryFn: ({ signal }) => fetchActivity(from, to, signal),
    });
}

/** Muscle groups for the Progress picker. */
export function useMuscles() {
    return useQuery<Muscle[]>({
        queryKey: ["muscles"],
        queryFn: ({ signal }) => fetchMuscles(signal),
        // Catalog is stable; keep it fresh for the session.
        staleTime: 5 * 60_000,
    });
}

/**
 * Exercises under a muscle. Disabled until a muscle is picked, so the empty
 * (no-selection) path fires no query.
 */
export function useExercises(muscleId: number | null) {
    return useQuery<Exercise[]>({
        queryKey: ["muscles", muscleId, "exercises"],
        queryFn: ({ signal }) => fetchExercises(muscleId as number, signal),
        enabled: muscleId != null,
        staleTime: 5 * 60_000,
    });
}

/**
 * Muscles ranked by the caller's training frequency (desc) — the Progress
 * muscle picker. The endpoint already returns frequency order; the UI renders
 * it verbatim (no client re-sort). A new user with no trainings gets `[]`,
 * which drives the empty state with no further queries fired.
 */
export function useTopMuscles() {
    return useQuery<TopMuscle[]>({
        queryKey: ["analytics", "top-muscles"],
        queryFn: ({ signal }) => fetchTopMuscles(signal),
        // Frequency shifts slowly within a session; keep it fresh.
        staleTime: 5 * 60_000,
    });
}

/**
 * A muscle's exercises ranked by training frequency (desc), all of them
 * (`limit=200`) — the Progress exercise picker. Disabled until a muscle name
 * is picked, so the empty path fires no query. Returned in frequency order;
 * rendered verbatim.
 */
export function useTopExercises(muscle: string | null) {
    return useQuery<TopExercise[]>({
        queryKey: ["analytics", "top-exercises", muscle, TOP_EXERCISES_LIMIT],
        queryFn: ({ signal }) =>
            fetchTopExercises(muscle as string, TOP_EXERCISES_LIMIT, signal),
        enabled: muscle != null,
        staleTime: 5 * 60_000,
    });
}

/**
 * Per-set progress series. Disabled until both muscle and exercise names are
 * chosen — the empty path does not query.
 */
export function useExerciseProgress(
    muscle: string | null,
    exercise: string | null,
) {
    return useQuery<ExerciseProgress>({
        queryKey: ["analytics", "exercise-progress", muscle, exercise],
        queryFn: ({ signal }) =>
            fetchExerciseProgress(muscle as string, exercise as string, signal),
        enabled: Boolean(muscle && exercise),
    });
}
