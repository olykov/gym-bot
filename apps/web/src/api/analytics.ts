/**
 * Analytics + catalog reads (spec §10.2/§10.3), typed by the generated contract.
 *
 * Thin functions over {@link apiRequest} that name each endpoint and pin its
 * response type to the `@api-contract` schema — the single source of truth. The
 * TanStack Query hooks in src/hooks/ wrap these for caching/loading/error.
 */
import type { Schemas } from "./client";
import { apiRequest } from "./client";

export type AnalyticsSummary = Schemas["AnalyticsSummary"];
export type ActivityDay = Schemas["ActivityDay"];
export type ExerciseProgress = Schemas["ExerciseProgress"];
export type ExerciseSetSeries = Schemas["ExerciseSetSeries"];
export type Muscle = Schemas["Muscle"];
export type Exercise = Schemas["Exercise"];
export type TopMuscle = Schemas["TopMuscle"];
export type TopExercise = Schemas["TopExercise"];

/** GET /analytics/summary — the four dashboard numbers (scoped to the caller). */
export function fetchSummary(signal?: AbortSignal): Promise<AnalyticsSummary> {
    return apiRequest<AnalyticsSummary>("/analytics/summary", { signal });
}

/**
 * GET /analytics/activity?from&to — one entry per active day in the range.
 *
 * @param from - inclusive start date (YYYY-MM-DD).
 * @param to - inclusive end date (YYYY-MM-DD).
 */
export function fetchActivity(
    from: string,
    to: string,
    signal?: AbortSignal,
): Promise<ActivityDay[]> {
    const qs = new URLSearchParams({ from, to }).toString();
    return apiRequest<ActivityDay[]>(`/analytics/activity?${qs}`, { signal });
}

/** GET /muscles — muscle groups visible to the caller. */
export function fetchMuscles(signal?: AbortSignal): Promise<Muscle[]> {
    return apiRequest<Muscle[]>("/muscles", { signal });
}

/** GET /muscles/{muscle_id}/exercises — exercises under a muscle. */
export function fetchExercises(
    muscleId: number,
    signal?: AbortSignal,
): Promise<Exercise[]> {
    return apiRequest<Exercise[]>(`/muscles/${muscleId}/exercises`, { signal });
}

/**
 * GET /analytics/top-muscles — muscles the caller has trained, ordered by
 * descending training frequency. Feeds the Progress muscle picker so the most-
 * trained muscle surfaces first (and seeds the on-mount default). The order is
 * authoritative — the UI renders it as-is, no client re-sort.
 */
export function fetchTopMuscles(signal?: AbortSignal): Promise<TopMuscle[]> {
    return apiRequest<TopMuscle[]>("/analytics/top-muscles", { signal });
}

/**
 * GET /analytics/top-exercises?muscle&limit — a muscle's exercises ordered by
 * descending training frequency. Feeds the Progress exercise picker.
 *
 * @param muscle - muscle group name.
 * @param limit - max exercises to return; pass 200 to get all of the muscle's.
 */
export function fetchTopExercises(
    muscle: string,
    limit: number,
    signal?: AbortSignal,
): Promise<TopExercise[]> {
    const qs = new URLSearchParams({
        muscle,
        limit: String(limit),
    }).toString();
    return apiRequest<TopExercise[]>(`/analytics/top-exercises?${qs}`, {
        signal,
    });
}

/**
 * GET /analytics/exercise-progress?muscle&exercise — per-set weight/reps series.
 *
 * @param muscle - muscle group name.
 * @param exercise - exercise name.
 */
export function fetchExerciseProgress(
    muscle: string,
    exercise: string,
    signal?: AbortSignal,
): Promise<ExerciseProgress> {
    const qs = new URLSearchParams({ muscle, exercise }).toString();
    return apiRequest<ExerciseProgress>(
        `/analytics/exercise-progress?${qs}`,
        { signal },
    );
}
