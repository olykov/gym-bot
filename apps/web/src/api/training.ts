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
export type TrainingCreate = Schemas["TrainingCreate"];
export type TrainingMove = Schemas["TrainingMove"];

/**
 * GET /training/days?from&to — one entry per training day, newest first.
 *
 * @param from - inclusive start date (YYYY-MM-DD).
 * @param to - inclusive end date (YYYY-MM-DD).
 * @param signal - optional AbortSignal.
 * @param tz - optional IANA timezone name. When provided, day boundaries are
 *   computed in that timezone so a session logged near midnight lands on the
 *   correct local calendar day.
 */
export function fetchTrainingDays(
    from: string,
    to: string,
    signal?: AbortSignal,
    tz?: string,
): Promise<TrainingDay[]> {
    const params: Record<string, string> = { from, to };
    if (tz) params.tz = tz;
    const qs = new URLSearchParams(params).toString();
    return apiRequest<TrainingDay[]>(`/training/days?${qs}`, { signal });
}

/**
 * GET /training/day/{date} — exercises (grouped) with their sets for one day.
 *
 * @param date - calendar date (YYYY-MM-DD).
 * @param signal - optional AbortSignal.
 * @param tz - optional IANA timezone name. When provided, day boundaries are
 *   computed in that timezone so a session logged near midnight lands on the
 *   correct local calendar day (mirrors `fetchTrainingDays`).
 */
export function fetchTrainingDay(
    date: string,
    signal?: AbortSignal,
    tz?: string,
): Promise<TrainingDayDetail> {
    const base = `/training/day/${encodeURIComponent(date)}`;
    const url = tz ? `${base}?${new URLSearchParams({ tz }).toString()}` : base;
    return apiRequest<TrainingDayDetail>(url, { signal });
}

/** POST /training — record one set; the server assigns id/date/user_id. */
export function createTraining(body: TrainingCreate): Promise<Training> {
    return apiRequest<Training>("/training", { method: "POST", body });
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

/**
 * PATCH /training/{training_id}/move — move a set to another day and/or exercise.
 *
 * At least one of {date, (muscle_name + exercise_name)} must be provided.
 * Returns the updated Training on success; throws ApiError on 409 (collision),
 * 422 (invalid), or 404 (not found / not owned).
 */
export function moveTraining(
    trainingId: string,
    body: TrainingMove,
): Promise<Training> {
    return apiRequest<Training>(
        `/training/${encodeURIComponent(trainingId)}/move`,
        { method: "PATCH", body },
    );
}
