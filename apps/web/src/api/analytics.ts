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
