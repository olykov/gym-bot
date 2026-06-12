/**
 * TanStack Query hooks for managing catalog elements (GYM-82/90/99/103) —
 * extracted from useRecord.ts in GYM-127 (file-size split, behavior
 * identical; useRecord re-exports everything so import sites are unchanged).
 *
 * Covers the ManageSheet actions: rename / delete / hide / move for muscles
 * and exercises, plus the GYM-103 hidden lists + unhide. Every mutation fans
 * out the shared list invalidation so tiles, top-lists and the "Show Hidden"
 * expander update immediately.
 */
import {
    useMutation,
    useQuery,
    useQueryClient,
    type QueryClient,
} from "@tanstack/react-query";
import {
    deleteExercise,
    deleteMuscle,
    fetchHiddenExercises,
    fetchHiddenMuscles,
    hideExercise,
    hideMuscle,
    moveExercise,
    renameExercise,
    renameMuscle,
    unhideExercise,
    unhideMuscle,
    type Exercise,
    type ExerciseMove,
    type ExerciseRename,
    type Muscle,
    type MuscleRename,
} from "@/api/analytics";
import { queryKeys } from "@/api/queryKeys";

/** Shared invalidation after any manage-element action (rename/delete/hide). */
function invalidateElementLists(qc: QueryClient): void {
    void qc.invalidateQueries({ queryKey: queryKeys.muscles.list });
    void qc.invalidateQueries({ queryKey: queryKeys.analytics.topMuscles });
    void qc.invalidateQueries({
        queryKey: queryKeys.analytics.topExercisesPrefix(),
    });
    // Invalidate all hidden-exercise caches so the "Show Hidden" expander appears
    // immediately after hiding an exercise (GYM-104 #2: the expander was invisible
    // because the hidden-exercises cache was not cleared after hide/unhide/move ops).
    void qc.invalidateQueries({ queryKey: queryKeys.exercises.hiddenPrefix });
}

interface RenameMuscleVars {
    muscleId: number;
    body: MuscleRename;
}

/**
 * PATCH /muscles/{id} — rename the caller's own private muscle (GYM-82).
 * On success invalidates the muscle + exercise lists and top lists so tiles
 * reflect the new name immediately.
 */
export function useRenameMuscle() {
    const qc = useQueryClient();
    return useMutation<Muscle, Error, RenameMuscleVars>({
        mutationFn: ({ muscleId, body }) => renameMuscle(muscleId, body),
        onSuccess: () => {
            invalidateElementLists(qc);
        },
    });
}

interface DeleteMuscleVars {
    muscleId: number;
}

/**
 * DELETE /muscles/{id} — delete the caller's own private muscle (GYM-82).
 * On success invalidates lists. A 409 (has history) is surfaced to the caller
 * to offer the Hide action instead.
 */
export function useDeleteMuscle() {
    const qc = useQueryClient();
    return useMutation<void, Error, DeleteMuscleVars>({
        mutationFn: ({ muscleId }) => deleteMuscle(muscleId),
        onSuccess: () => {
            invalidateElementLists(qc);
        },
    });
}

interface HideMuscleVars {
    muscleId: number;
}

/**
 * PUT /muscles/{id}/hidden — hide a global catalog muscle from the caller's
 * picker (GYM-82). On success invalidates the muscle + exercise lists.
 */
export function useHideMuscle() {
    const qc = useQueryClient();
    return useMutation<void, Error, HideMuscleVars>({
        mutationFn: ({ muscleId }) => hideMuscle(muscleId),
        onSuccess: () => {
            invalidateElementLists(qc);
        },
    });
}

interface RenameExerciseVars {
    exerciseId: number;
    muscleName: string;
    body: ExerciseRename;
}

/**
 * PATCH /exercises/{id} — rename the caller's own private exercise (GYM-82).
 * On success invalidates the exercise lists for the muscle plus top-exercises
 * so tiles + progress charts that key on the name pick up the new value.
 */
export function useRenameExercise() {
    const qc = useQueryClient();
    return useMutation<Exercise, Error, RenameExerciseVars>({
        mutationFn: ({ exerciseId, body }) => renameExercise(exerciseId, body),
        onSuccess: (_data, vars) => {
            invalidateElementLists(qc);
            // Also invalidate the exercise-progress series (keyed by exercise name)
            // so any Progress chart for the old name refreshes.
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseProgressPrefix(),
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topExercisesPrefix(
                    vars.muscleName,
                ),
            });
        },
    });
}

interface DeleteExerciseVars {
    exerciseId: number;
}

/**
 * DELETE /exercises/{id} — delete the caller's own private exercise (GYM-82).
 * A 409 (has history) is surfaced to the caller to offer Hide instead.
 */
export function useDeleteExercise() {
    const qc = useQueryClient();
    return useMutation<void, Error, DeleteExerciseVars>({
        mutationFn: ({ exerciseId }) => deleteExercise(exerciseId),
        onSuccess: () => {
            invalidateElementLists(qc);
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseProgressPrefix(),
            });
        },
    });
}

interface HideExerciseVars {
    exerciseId: number;
}

/**
 * PUT /exercises/{id}/hidden — hide a global catalog exercise from the caller's
 * picker (GYM-82). On success invalidates the exercise lists.
 */
export function useHideExercise() {
    const qc = useQueryClient();
    return useMutation<void, Error, HideExerciseVars>({
        mutationFn: ({ exerciseId }) => hideExercise(exerciseId),
        onSuccess: () => {
            invalidateElementLists(qc);
        },
    });
}

interface MoveExerciseVars {
    exerciseId: number;
    body: ExerciseMove;
}

/**
 * PATCH /exercises/{id}/muscle — move the caller's own exercise to another
 * muscle (GYM-90). On success invalidates the muscle + exercise lists and
 * top-muscles/top-exercises so the exercise appears under the new muscle and
 * disappears from the old one. The exercise-progress series is also invalidated
 * since the muscle context changed.
 * 403: exercise is global (not movable). 404: exercise or target muscle not
 * found. 409: name collision in the target muscle — surfaced to the caller.
 */
export function useMoveExercise() {
    const qc = useQueryClient();
    return useMutation<Exercise, Error, MoveExerciseVars>({
        mutationFn: ({ exerciseId, body }) => moveExercise(exerciseId, body),
        onSuccess: () => {
            invalidateElementLists(qc);
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseProgressPrefix(),
            });
        },
    });
}

// ── GYM-103: Show Hidden + Unhide ────────────────────────────────────────────

/**
 * GET /muscles/hidden — the global muscles the caller has hidden (GYM-102/103).
 * Powers the "Show Hidden" expander at the bottom of the muscle picker.
 * Returns [] when nothing is hidden; the expander is omitted entirely in that
 * case (no empty-state query fan-out on the happy path).
 */
export function useHiddenMuscles() {
    return useQuery<Muscle[]>({
        queryKey: queryKeys.muscles.hidden,
        queryFn: ({ signal }) => fetchHiddenMuscles(signal),
        staleTime: 5 * 60_000,
    });
}

/**
 * GET /exercises/hidden?muscle=<name> — the global exercises hidden for one
 * muscle (GYM-102/103). Powers the "Show Hidden" expander on the exercise step.
 * Disabled until a muscle name is provided so the empty path fires no query.
 *
 * @param muscleName - muscle group name; pass null to disable the query.
 */
export function useHiddenExercises(muscleName: string | null) {
    return useQuery<Exercise[]>({
        queryKey: queryKeys.exercises.hidden(muscleName),
        queryFn: ({ signal }) =>
            fetchHiddenExercises(muscleName as string, signal),
        enabled: muscleName != null,
        staleTime: 5 * 60_000,
    });
}

interface UnhideMuscleVars {
    muscleId: number;
}

/**
 * DELETE /muscles/{id}/hidden — unhide a previously hidden global muscle
 * (GYM-103). On success invalidates the visible muscle list, top-muscles, and
 * the hidden-muscles list so both lists update immediately.
 */
export function useUnhideMuscle() {
    const qc = useQueryClient();
    return useMutation<void, Error, UnhideMuscleVars>({
        mutationFn: ({ muscleId }) => unhideMuscle(muscleId),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: queryKeys.muscles.list });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topMuscles,
            });
            void qc.invalidateQueries({ queryKey: queryKeys.muscles.hidden });
        },
    });
}

interface UnhideExerciseVars {
    exerciseId: number;
    muscleName: string;
}

/**
 * DELETE /exercises/{id}/hidden — unhide a previously hidden global exercise
 * (GYM-103). On success invalidates the visible exercises list, top-exercises,
 * and the hidden-exercises list for the muscle so both lists update immediately.
 */
export function useUnhideExercise() {
    const qc = useQueryClient();
    return useMutation<void, Error, UnhideExerciseVars>({
        mutationFn: ({ exerciseId }) => unhideExercise(exerciseId),
        onSuccess: (_data, vars) => {
            void qc.invalidateQueries({ queryKey: queryKeys.muscles.list });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topMuscles,
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topExercisesPrefix(),
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.exercises.hidden(vars.muscleName),
            });
        },
    });
}
