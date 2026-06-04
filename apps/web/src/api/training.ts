/**
 * Training reads + mutations for the History feature (spec §11), typed by the
 * generated contract.
 *
 * Thin functions over {@link apiRequest} that name each endpoint and pin its
 * request/response type to the `@api-contract` schema — the single source of
 * truth. The TanStack Query hooks in src/hooks/useTraining.ts wrap these for
 * caching / loading / error and the optimistic edit+delete logic.
 */
import type { Schemas } from "./client";
import { apiRequest } from "./client";

export type TrainingDay = Schemas["TrainingDay"];
export type TrainingDayDetail = Schemas["TrainingDayDetail"];
export type TrainingDayExercise = Schemas["TrainingDayExercise"];
export type TrainingSet = Schemas["TrainingSet"];
export type TrainingUpdate = Schemas["TrainingUpdate"];
export type Training = Schemas["Training"];

/**
 * GET /training/days?from&to — one entry per training day, newest first.
 *
 * @param from - inclusive start date (YYYY-MM-DD).
 * @param to - inclusive end date (YYYY-MM-DD).
 */
export function fetchTrainingDays(
    from: string,
    to: string,
    signal?: AbortSignal,
): Promise<TrainingDay[]> {
    const qs = new URLSearchParams({ from, to }).toString();
    return apiRequest<TrainingDay[]>(`/training/days?${qs}`, { signal });
}

/** GET /training/day/{date} — exercises (grouped) with their sets for one day. */
export function fetchTrainingDay(
    date: string,
    signal?: AbortSignal,
): Promise<TrainingDayDetail> {
    return apiRequest<TrainingDayDetail>(
        `/training/day/${encodeURIComponent(date)}`,
        { signal },
    );
}

/** PUT /training/{training_id} — update a set's weight and reps. */
export function updateTraining(
    trainingId: string,
    body: TrainingUpdate,
): Promise<Training> {
    return apiRequest<Training>(
        `/training/${encodeURIComponent(trainingId)}`,
        { method: "PUT", body },
    );
}

/** DELETE /training/{training_id} — remove a set (204, no body). */
export function deleteTraining(trainingId: string): Promise<void> {
    return apiRequest<void>(`/training/${encodeURIComponent(trainingId)}`, {
        method: "DELETE",
    });
}
