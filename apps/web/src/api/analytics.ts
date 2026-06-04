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
export type RecentExercise = Schemas["RecentExercise"];
export type CompletedSets = Schemas["CompletedSets"];
export type PersonalRecord = Schemas["PersonalRecord"];
export type MaxReps = Schemas["MaxReps"];
export type MuscleCreate = Schemas["MuscleCreate"];
export type ExerciseCreate = Schemas["ExerciseCreate"];

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

/**
 * GET /analytics/recent-exercises?limit — the caller's most-recently-trained
 * distinct exercises (cross-muscle, newest first), each carrying the last
 * working set's weight/reps. Powers the record flow's fast lane and the
 * cold-open pre-fill in a single read (spec §12.9).
 *
 * @param limit - max exercises to return (the fast lane uses 8).
 */
export function fetchRecentExercises(
    limit: number,
    signal?: AbortSignal,
): Promise<RecentExercise[]> {
    const qs = new URLSearchParams({ limit: String(limit) }).toString();
    return apiRequest<RecentExercise[]>(`/analytics/recent-exercises?${qs}`, {
        signal,
    });
}

/**
 * GET /analytics/completed-sets?muscle&exercise&date — the set NUMBERS already
 * recorded for an exercise on a date. Drives the record flow's auto set-number
 * (spec §12.3) so the user never picks a set number.
 *
 * @param muscle - muscle group name.
 * @param exercise - exercise name.
 * @param date - calendar date (YYYY-MM-DD), usually today.
 */
export function fetchCompletedSets(
    muscle: string,
    exercise: string,
    date: string,
    signal?: AbortSignal,
): Promise<CompletedSets> {
    const qs = new URLSearchParams({ muscle, exercise, date }).toString();
    return apiRequest<CompletedSets>(`/analytics/completed-sets?${qs}`, {
        signal,
    });
}

/**
 * GET /analytics/personal-record?muscle&exercise — the caller's heaviest set
 * for an exercise, or `null` when there's no history. Labels the PR target chip
 * and is the cold-open pre-fill fallback (spec §12.3).
 *
 * @param muscle - muscle group name.
 * @param exercise - exercise name.
 */
export function fetchPersonalRecord(
    muscle: string,
    exercise: string,
    signal?: AbortSignal,
): Promise<PersonalRecord | null> {
    const qs = new URLSearchParams({ muscle, exercise }).toString();
    return apiRequest<PersonalRecord | null>(
        `/analytics/personal-record?${qs}`,
        { signal },
    );
}

/**
 * POST /muscles — create a private muscle for the caller (add-inline, spec
 * §12.2). Returns the created (or existing) muscle row.
 */
export function createMuscle(body: MuscleCreate): Promise<Muscle> {
    return apiRequest<Muscle>("/muscles", { method: "POST", body });
}

/**
 * POST /exercises — create a private exercise under a muscle, referenced by
 * name (the muscle is created if needed, per contract). Add-inline (spec §12.2).
 */
export function createExercise(body: ExerciseCreate): Promise<Exercise> {
    return apiRequest<Exercise>("/exercises", { method: "POST", body });
}
