/**
 * TanStack Query hooks for the History feature (spec §11) — mirrors
 * useAnalytics.ts. Day-list + day-detail reads, plus the edit/delete mutations
 * with optimistic `onMutate` patches, `onError` rollback, and the mandatory
 * cross-screen invalidation on settle (§11.4).
 *
 * The set's `training_id` is the mutation key everywhere — never a list index
 * (§11.7) — so an optimistic patch/removal always hits the right row.
 */
import {
    keepPreviousData,
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";
import {
    createTraining,
    deleteTraining,
    fetchTrainingDay,
    fetchTrainingDays,
    moveTraining,
    updateTraining,
    type TrainingCreate,
    type TrainingDay,
    type TrainingDayDetail,
    type TrainingMove,
    type TrainingUpdate,
} from "@/api/training";
import { DEVICE_TZ } from "@/lib/timezone";

/**
 * Query key for one window of the day list (consistent with activity's key).
 *
 * DEVICE_TZ is included so that a timezone change (across reloads) produces a
 * cache miss and the server regroups days in the correct local timezone.
 */
export function daysKey(from: string, to: string) {
    return ["training", "days", from, to, DEVICE_TZ ?? "UTC"] as const;
}
/** Query key for one day's detail. */
export function dayKey(date: string) {
    return ["training", "day", date] as const;
}

/**
 * Day list for a date window (§11.2). Newest-first from the API.
 *
 * `placeholderData: keepPreviousData` keeps the previous window's list rendered
 * while a wider "load earlier" window fetches under a new query key, so there's
 * no blank flash on infinite-scroll load-more (GYM-53 #4). Only the very first
 * load (no prior data) shows skeletons; `isPlaceholderData` flags the in-flight
 * widen so the page never renders a full skeleton over the kept list.
 *
 * DEVICE_TZ is forwarded so that day-boundary grouping respects the user's
 * local timezone (e.g. a session at 23:00 Asia/Tbilisi lands on the correct
 * local date rather than the next UTC day).
 */
export function useTrainingDays(from: string, to: string) {
    return useQuery<TrainingDay[]>({
        queryKey: daysKey(from, to),
        queryFn: ({ signal }) => fetchTrainingDays(from, to, signal, DEVICE_TZ),
        placeholderData: keepPreviousData,
    });
}

/** One day's grouped exercises + sets (§11.3). */
export function useTrainingDay(date: string) {
    return useQuery<TrainingDayDetail>({
        queryKey: dayKey(date),
        queryFn: ({ signal }) => fetchTrainingDay(date, signal),
    });
}

/**
 * Invalidate every key a set edit/delete can move (§11.4): the day, all day-list
 * windows, and the analytics surfaces (a weight edit can change a PR/streak/cell)
 * so Dashboard and Progress never show stale numbers after an edit.
 *
 * GYM-105: also invalidates log-context (all exercises, all dates) so that an
 * already-open SetLogger — and the next open — reflects the deleted/edited set
 * immediately. The broad prefix covers every muscle/exercise combination; the
 * query is small, so the extra refetch cost is negligible. exercise-progress is
 * also covered (already was) because an edit can change the per-exercise PR.
 */
function invalidateAfterMutation(
    qc: ReturnType<typeof useQueryClient>,
    date: string,
): void {
    void qc.invalidateQueries({ queryKey: dayKey(date) });
    void qc.invalidateQueries({ queryKey: ["training", "days"] });
    void qc.invalidateQueries({ queryKey: ["analytics", "summary"] });
    void qc.invalidateQueries({ queryKey: ["analytics", "activity"] });
    void qc.invalidateQueries({ queryKey: ["analytics", "exercise-progress"] });
    // GYM-105: invalidate ALL log-context entries (by broad prefix) so the
    // SetLogger never shows deleted sets as ✓ and always shows the real PR.
    void qc.invalidateQueries({ queryKey: ["analytics", "log-context"] });
}

interface EditVars {
    trainingId: string;
    body: TrainingUpdate;
}

/**
 * Optimistically patch a set's weight/reps in the day detail (§11.4).
 *
 * Snapshots the detail in `onMutate`, patches the matching `training_id` in
 * place (`sets_count` is unchanged), rolls back on error, and invalidates the
 * cross-screen key set on settle. The caller closes the sheet immediately.
 */
export function useEditSet(date: string) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ trainingId, body }: EditVars) =>
            updateTraining(trainingId, body),
        onMutate: async ({ trainingId, body }: EditVars) => {
            await qc.cancelQueries({ queryKey: dayKey(date) });
            const previous = qc.getQueryData<TrainingDayDetail>(dayKey(date));
            if (previous) {
                qc.setQueryData<TrainingDayDetail>(dayKey(date), {
                    ...previous,
                    exercises: previous.exercises.map((ex) => ({
                        ...ex,
                        sets: ex.sets.map((s) =>
                            s.training_id === trainingId
                                ? { ...s, weight: body.weight, reps: body.reps }
                                : s,
                        ),
                    })),
                });
            }
            return { previous };
        },
        onError: (_err, _vars, ctx) => {
            if (ctx?.previous) qc.setQueryData(dayKey(date), ctx.previous);
        },
        onSettled: () => invalidateAfterMutation(qc, date),
    });
}

/**
 * Optimistically remove a set from the day detail (§11.4).
 *
 * Snapshots, removes the matching `training_id` (dropping its exercise group if
 * it was the last set), rolls back on error, and invalidates the cross-screen
 * key set on settle. `isEmptyAfter` (returned via the mutation result/context)
 * lets the page navigate back when the day becomes empty.
 */
export function useDeleteSet(date: string) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (trainingId: string) => deleteTraining(trainingId),
        onMutate: async (trainingId: string) => {
            await qc.cancelQueries({ queryKey: dayKey(date) });
            const previous = qc.getQueryData<TrainingDayDetail>(dayKey(date));
            if (previous) {
                const exercises = previous.exercises
                    .map((ex) => ({
                        ...ex,
                        sets: ex.sets.filter(
                            (s) => s.training_id !== trainingId,
                        ),
                    }))
                    // Drop an exercise group once its last set is gone.
                    .filter((ex) => ex.sets.length > 0);
                qc.setQueryData<TrainingDayDetail>(dayKey(date), {
                    ...previous,
                    exercises,
                });
            }
            return { previous };
        },
        onError: (_err, _vars, ctx) => {
            if (ctx?.previous) qc.setQueryData(dayKey(date), ctx.previous);
        },
        onSettled: () => invalidateAfterMutation(qc, date),
    });
}

interface AddSetVars {
    body: TrainingCreate;
}

/**
 * Add a set retroactively to a specific day/exercise (GYM-51).
 *
 * No optimistic patch — the set number and server-assigned id must come from
 * the API response before we can insert accurately. Invalidates on settle so
 * the day detail re-fetches with the new set included. Also invalidates the
 * cross-screen analytics keys (a new set can change summary/activity/progress).
 */
export function useAddSet(date: string) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ body }: AddSetVars) => createTraining(body),
        onSettled: () => invalidateAfterMutation(qc, date),
    });
}

interface MoveSetVars {
    trainingId: string;
    body: TrainingMove;
    /** The target date (if different from the source) — must also be invalidated. */
    targetDate?: string;
}

/**
 * Move a set to another day and/or exercise (GYM-51 PATCH /training/{id}/move).
 *
 * Optimistically removes the set from the source day-detail cache so it
 * disappears immediately. On error rolls back. On settle invalidates both the
 * source day and the target day (if different), plus all analytics keys.
 */
export function useMoveSet(sourceDate: string) {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ trainingId, body }: MoveSetVars) =>
            moveTraining(trainingId, body),
        onMutate: async ({ trainingId }: MoveSetVars) => {
            await qc.cancelQueries({ queryKey: dayKey(sourceDate) });
            const previous = qc.getQueryData<TrainingDayDetail>(
                dayKey(sourceDate),
            );
            if (previous) {
                const exercises = previous.exercises
                    .map((ex) => ({
                        ...ex,
                        sets: ex.sets.filter(
                            (s) => s.training_id !== trainingId,
                        ),
                    }))
                    .filter((ex) => ex.sets.length > 0);
                qc.setQueryData<TrainingDayDetail>(dayKey(sourceDate), {
                    ...previous,
                    exercises,
                });
            }
            return { previous };
        },
        onError: (_err, _vars, ctx) => {
            if (ctx?.previous)
                qc.setQueryData(dayKey(sourceDate), ctx.previous);
        },
        onSettled: (_data, _err, vars) => {
            // Always invalidate the source day.
            invalidateAfterMutation(qc, sourceDate);
            // Also invalidate the target day if it differs from the source.
            if (vars?.targetDate && vars.targetDate !== sourceDate) {
                invalidateAfterMutation(qc, vars.targetDate);
            }
        },
    });
}
