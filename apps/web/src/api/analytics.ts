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
export type PersonalRecord = Schemas["PersonalRecord"];
export type LogContext = Schemas["LogContext"];
export type LogSet = Schemas["LogSet"];
export type MaxReps = Schemas["MaxReps"];
export type MuscleCreate = Schemas["MuscleCreate"];
export type ExerciseCreate = Schemas["ExerciseCreate"];
export type MuscleRename = Schemas["MuscleRename"];
export type ExerciseRename = Schemas["ExerciseRename"];
export type ExerciseMove = Schemas["ExerciseMove"];
export type ExerciseCandidate = Schemas["ExerciseCandidate"];

/**
 * GET /analytics/summary — the four dashboard numbers (scoped to the caller).
 *
 * @param tz - optional IANA timezone name (e.g. "Asia/Tbilisi"). When
 *   provided, streak and weekly buckets are computed in that timezone.
 *   Omit to keep the original UTC behaviour.
 */
export function fetchSummary(
    signal?: AbortSignal,
    tz?: string,
): Promise<AnalyticsSummary> {
    const params: Record<string, string> = {};
    if (tz) params.tz = tz;
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `/analytics/summary?${qs}` : "/analytics/summary";
    return apiRequest<AnalyticsSummary>(url, { signal });
}

/**
 * GET /analytics/activity?from&to — one entry per active day in the range.
 *
 * @param from - inclusive start date (YYYY-MM-DD).
 * @param to - inclusive end date (YYYY-MM-DD).
 * @param signal - optional AbortSignal.
 * @param tz - optional IANA timezone name. When provided, day boundaries are
 *   computed in that timezone instead of UTC.
 */
export function fetchActivity(
    from: string,
    to: string,
    signal?: AbortSignal,
    tz?: string,
): Promise<ActivityDay[]> {
    const params: Record<string, string> = { from, to };
    if (tz) params.tz = tz;
    const qs = new URLSearchParams(params).toString();
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
 * GET /analytics/log-context?muscle&exercise&date — the single set-logger
 * context read (spec §12.3, GYM-71): the set numbers already logged on the date,
 * the most recent prior session's sets (for last-session pre-fill), and the
 * personal record (for the PR chip). One round-trip replaces the old three reads
 * (completed-sets + personal-record + recent pre-fill).
 *
 * @param muscle - muscle group name.
 * @param exercise - exercise name.
 * @param date - calendar date (YYYY-MM-DD), usually today.
 */
export function fetchLogContext(
    muscle: string,
    exercise: string,
    date: string,
    signal?: AbortSignal,
): Promise<LogContext> {
    const qs = new URLSearchParams({ muscle, exercise, date }).toString();
    return apiRequest<LogContext>(`/analytics/log-context?${qs}`, { signal });
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

/**
 * PATCH /muscles/{muscle_id} — rename the caller's own private muscle (GYM-80).
 * Returns 403 on a global/not-owned muscle, 409 on a duplicate name, 422 on
 * an invalid name.
 */
export function renameMuscle(muscleId: number, body: MuscleRename): Promise<Muscle> {
    return apiRequest<Muscle>(`/muscles/${muscleId}`, { method: "PATCH", body });
}

/**
 * DELETE /muscles/{muscle_id} — delete the caller's own private muscle (GYM-80).
 * Returns 204 on success, 409 when the muscle has logged training history
 * (caller should offer Hide instead).
 */
export function deleteMuscle(muscleId: number): Promise<void> {
    return apiRequest<void>(`/muscles/${muscleId}`, { method: "DELETE" });
}

/**
 * PUT /muscles/{muscle_id}/hidden — hide a global catalog muscle from the
 * caller's picker (GYM-80). Returns 204.
 */
export function hideMuscle(muscleId: number): Promise<void> {
    return apiRequest<void>(`/muscles/${muscleId}/hidden`, { method: "PUT" });
}

/**
 * PATCH /exercises/{exercise_id} — rename the caller's own private exercise
 * (GYM-80). Returns 403/409/422 under the same rules as renameMuscle.
 */
export function renameExercise(exerciseId: number, body: ExerciseRename): Promise<Exercise> {
    return apiRequest<Exercise>(`/exercises/${exerciseId}`, { method: "PATCH", body });
}

/**
 * DELETE /exercises/{exercise_id} — delete the caller's own private exercise
 * (GYM-80). Returns 204 on success, 409 when it has logged history.
 */
export function deleteExercise(exerciseId: number): Promise<void> {
    return apiRequest<void>(`/exercises/${exerciseId}`, { method: "DELETE" });
}

/**
 * PUT /exercises/{exercise_id}/hidden — hide a global catalog exercise from
 * the caller's picker (GYM-80). Returns 204.
 */
export function hideExercise(exerciseId: number): Promise<void> {
    return apiRequest<void>(`/exercises/${exerciseId}/hidden`, { method: "PUT" });
}

/**
 * PATCH /exercises/{exercise_id}/muscle — move the caller's own exercise to
 * another muscle (GYM-90). Returns the updated Exercise on success.
 * 403: exercise is global/canonical. 404: exercise or target muscle not found.
 * 409: caller already has an exercise with that name in the target muscle.
 */
export function moveExercise(exerciseId: number, body: ExerciseMove): Promise<Exercise> {
    return apiRequest<Exercise>(`/exercises/${exerciseId}/muscle`, { method: "PATCH", body });
}

/**
 * GET /muscles/hidden — the global muscles the caller has hidden (GYM-102).
 * Powers the "Show Hidden" expander in the muscle picker step. Returns [] when
 * nothing is hidden.
 */
export function fetchHiddenMuscles(signal?: AbortSignal): Promise<Muscle[]> {
    return apiRequest<Muscle[]>("/muscles/hidden", { signal });
}

/**
 * GET /exercises/hidden?muscle=<name> — the global exercises the caller has
 * hidden within a muscle (GYM-102). Powers the "Show Hidden" expander in the
 * exercise picker step. Returns [] when nothing is hidden for that muscle.
 *
 * @param muscle - muscle group name.
 */
export function fetchHiddenExercises(
    muscle: string,
    signal?: AbortSignal,
): Promise<Exercise[]> {
    const qs = new URLSearchParams({ muscle }).toString();
    return apiRequest<Exercise[]>(`/exercises/hidden?${qs}`, { signal });
}

/**
 * DELETE /muscles/{muscle_id}/hidden — unhide a previously hidden global muscle
 * (GYM-102). Returns 204 on success; the muscle returns to the visible list.
 */
export function unhideMuscle(muscleId: number): Promise<void> {
    return apiRequest<void>(`/muscles/${muscleId}/hidden`, { method: "DELETE" });
}

/**
 * DELETE /exercises/{exercise_id}/hidden — unhide a previously hidden global
 * exercise (GYM-102). Returns 204; the exercise returns to the visible list.
 */
export function unhideExercise(exerciseId: number): Promise<void> {
    return apiRequest<void>(`/exercises/${exerciseId}/hidden`, { method: "DELETE" });
}

/**
 * GET /exercises/search?q=&muscle_id=&lang=&limit= — ranked exercise candidates
 * for the search-and-pick dropdown (GYM-94, ADR 0003 Channel B).
 *
 * Returns candidates ordered best-match-first. Scoped to a single muscle when
 * `muscleId` is provided; otherwise the whole catalog is searched.
 *
 * @param q - the user's typed search query.
 * @param muscleId - optional muscle scope.
 * @param lang - resolved locale (ISO-639-1) from getLocale()/GYM-108.
 * @param limit - max candidates to return.
 * @param signal - optional AbortSignal.
 */
export function searchExercises(
    q: string,
    muscleId?: number,
    lang?: string,
    limit?: number,
    signal?: AbortSignal,
): Promise<ExerciseCandidate[]> {
    const params: Record<string, string> = { q };
    if (muscleId !== undefined) params.muscle_id = String(muscleId);
    if (lang) params.lang = lang;
    if (limit !== undefined) params.limit = String(limit);
    const qs = new URLSearchParams(params).toString();
    return apiRequest<ExerciseCandidate[]>(`/exercises/search?${qs}`, { signal });
}
