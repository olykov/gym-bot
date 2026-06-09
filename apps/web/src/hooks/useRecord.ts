/**
 * TanStack Query hooks for the record-training flow (spec §12). The picker read
 * (log-context), the catalog create mutations (muscle/exercise add-inline), the
 * `POST /training` mutation that logs a set and fans out the §12.5 cross-screen
 * invalidation, and the prefetch helpers (§12.5) that warm reads so each pick is
 * snappy.
 *
 * Phase B is powered by ONE read — `GET /analytics/log-context` (GYM-71): the
 * set numbers already logged today, the last prior session's sets (last-session
 * pre-fill), and the personal record (PR chip). It replaces the old three reads
 * (completed-sets + personal-record + the recent pre-fill) → one round-trip.
 *
 * Every read fires only when the sheet needs it: log-context stays disabled
 * until an exercise is chosen — the empty path fires nothing (ARCH §2). Reads
 * carry a long staleTime/gcTime so a warmed session stays instant.
 */
import {
    useMutation,
    useQuery,
    useQueryClient,
    type QueryClient,
} from "@tanstack/react-query";
import {
    createExercise,
    createMuscle,
    deleteExercise,
    deleteMuscle,
    fetchExercises,
    fetchHiddenExercises,
    fetchHiddenMuscles,
    fetchLogContext,
    fetchTopExercises,
    fetchTopMuscles,
    hideExercise,
    hideMuscle,
    moveExercise,
    renameExercise,
    renameMuscle,
    searchExercises,
    unhideExercise,
    unhideMuscle,
    type Exercise,
    type ExerciseCandidate,
    type ExerciseCreate,
    type ExerciseMove,
    type ExerciseRename,
    type LogContext,
    type Muscle,
    type MuscleCreate,
    type MuscleRename,
} from "@/api/analytics";
import { fetchTrainingDay } from "@/api/training";
import {
    createTraining,
    type Training,
    type TrainingCreate,
} from "@/api/training";

/** Pull-all sentinel for a muscle's exercises (mirrors useAnalytics). */
const TOP_EXERCISES_LIMIT = 200;

/**
 * Long cache window for the record-flow reads (spec §12.5 perf): once a read is
 * warm during a logging session it stays instant — top-muscles / exercises /
 * the day / log-context don't meaningfully change mid-session, and a save
 * invalidates the keys it actually moves.
 */
const SESSION_STALE = 10 * 60_000;
const SESSION_GC = 10 * 60_000;

/** Query key for one exercise's log-context on a date. */
export function logContextKey(
    muscle: string | null,
    exercise: string | null,
    date: string,
) {
    return ["analytics", "log-context", muscle, exercise, date] as const;
}

/**
 * The single Phase-B read (§12.3): completed set numbers + last session's sets +
 * the PR, in one round-trip. Disabled until both names exist, so Phase A fires
 * nothing.
 *
 * GYM-105: staleTime is intentionally 0 so React Query ALWAYS refetches on
 * mount (i.e. every time the SetLogger opens for an exercise). This fixes the
 * prod-verified bug where reopening within the 10-min SESSION_STALE window
 * served a stale cache snapshot that still contained deleted sets as ✓ and
 * showed no PR. gcTime is kept at SESSION_GC so the previous snapshot renders
 * INSTANTLY as a placeholder while the fresh fetch runs in the background —
 * the instant feel is preserved, but the server truth always arrives and
 * replaces the stale data. The query is small and sargable (GYM-59), so the
 * per-open refetch is cheap.
 */
export function useLogContext(
    muscle: string | null,
    exercise: string | null,
    date: string,
) {
    return useQuery<LogContext>({
        queryKey: logContextKey(muscle, exercise, date),
        queryFn: ({ signal }) =>
            fetchLogContext(muscle as string, exercise as string, date, signal),
        enabled: Boolean(muscle && exercise),
        staleTime: 0,
        gcTime: SESSION_GC,
        refetchOnMount: "always",
    });
}

/** Add-inline: create a private muscle, then refresh the muscle catalog. */
export function useCreateMuscle() {
    const qc = useQueryClient();
    return useMutation<Muscle, Error, MuscleCreate>({
        mutationFn: (body) => createMuscle(body),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: ["muscles"] });
            void qc.invalidateQueries({ queryKey: ["analytics", "top-muscles"] });
        },
    });
}

/** Add-inline: create a private exercise under a muscle name, then refresh. */
export function useCreateExercise() {
    const qc = useQueryClient();
    return useMutation<Exercise, Error, ExerciseCreate>({
        mutationFn: (body) => createExercise(body),
        onSuccess: (data, vars) => {
            void qc.invalidateQueries({ queryKey: ["muscles"] });
            void qc.invalidateQueries({
                queryKey: ["analytics", "top-exercises", vars.muscle_name],
            });
            // GYM-100 fix #3: after add→resolve (resolution=existing or resolution=unhidden),
            // the GYM-99 server now correctly returns the exercise's real PR/history instead
            // of a cached empty context. Invalidate the log-context for the resolved exercise
            // (by muscle+exercise prefix, covering all dates) so SetLogger re-fetches instead
            // of serving a 10-min-stale empty result. Use the canonical name the backend
            // returned (data.name), not the user-typed name, since the resolution may have
            // matched a differently-cased or trimmed name.
            void qc.invalidateQueries({
                queryKey: ["analytics", "log-context", vars.muscle_name, data.name],
            });
            // Also invalidate exercise-progress for the canonical name so the Progress chart
            // is not stale if the user re-adds a previously tracked exercise.
            void qc.invalidateQueries({
                queryKey: [
                    "analytics",
                    "exercise-progress",
                    vars.muscle_name,
                    data.name,
                ],
            });
        },
    });
}

/**
 * Log one set (`POST /training`) and fan out the §12.5 cross-screen
 * invalidation on settle. We do NOT optimistically patch other screens — the
 * sheet shows its own recap; the rest of the app just re-fetches. A new set can
 * move the streak/sets/PR (Dashboard), the activity cell, the progress chart,
 * today's History day, the log-context (auto set #/PR), and recency, so every
 * one of those keys is invalidated. `today` is the day-detail key to refresh.
 *
 * On error the caller keeps the sheet open and surfaces an inline message; it
 * does NOT advance the set number or append the recap (so the recap never lies,
 * §12.5).
 */
export function useCreateTraining(today: string) {
    const qc = useQueryClient();
    return useMutation<Training, Error, TrainingCreate>({
        mutationFn: (body) => createTraining(body),
        onSettled: (_data, _err, vars) => {
            void qc.invalidateQueries({ queryKey: ["analytics", "summary"] });
            void qc.invalidateQueries({ queryKey: ["analytics", "activity"] });
            void qc.invalidateQueries({
                queryKey: [
                    "analytics",
                    "log-context",
                    vars.muscle_name,
                    vars.exercise_name,
                ],
            });
            void qc.invalidateQueries({
                queryKey: [
                    "analytics",
                    "exercise-progress",
                    vars.muscle_name,
                    vars.exercise_name,
                ],
            });
            void qc.invalidateQueries({ queryKey: ["training", "days"] });
            void qc.invalidateQueries({ queryKey: ["training", "day", today] });
        },
    });
}

/**
 * Warm the picker reads on sheet open (spec §12.5 perf): the muscle tiles
 * (`top-muscles`) and today's training (the Continue tile). Long staleTime so
 * the first paint after open is instant. Fired only when the sheet opens — never
 * on app mount (ARCH §2).
 */
export function prefetchPickerReads(qc: QueryClient, today: string): void {
    void qc.prefetchQuery({
        queryKey: ["analytics", "top-muscles"],
        queryFn: ({ signal }) => fetchTopMuscles(signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
    void qc.prefetchQuery({
        queryKey: ["training", "day", today],
        queryFn: ({ signal }) => fetchTrainingDay(today, signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
}

/**
 * Prefetch a muscle's exercises on muscle pick (spec §12.5 perf) so the exercise
 * tiles appear instantly. Warms both:
 * - top-exercises (for the frequency-sort map used to order the full catalog)
 * - /muscles/{id}/exercises (the full catalog that is now the tile source, GYM-83)
 *
 * @param muscle - muscle name (for the top-exercises key).
 * @param muscleId - numeric muscle id; if null, full-exercises prefetch is skipped.
 */
export function prefetchMuscleExercises(
    qc: QueryClient,
    muscle: string,
    muscleId: number | null,
): void {
    void qc.prefetchQuery({
        queryKey: ["analytics", "top-exercises", muscle, TOP_EXERCISES_LIMIT],
        queryFn: ({ signal }) =>
            fetchTopExercises(muscle, TOP_EXERCISES_LIMIT, signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
    if (muscleId != null) {
        void qc.prefetchQuery({
            queryKey: ["muscles", muscleId, "exercises"],
            queryFn: ({ signal }) => fetchExercises(muscleId, signal),
            staleTime: SESSION_STALE,
            gcTime: SESSION_GC,
        });
    }
}

/**
 * Prefetch the log-context for an exercise (spec §12.5 perf) — used to warm the
 * Continue tile's exercise so tapping it lands in a pre-filled Phase B.
 */
export function prefetchLogContext(
    qc: QueryClient,
    muscle: string,
    exercise: string,
    date: string,
): void {
    void qc.prefetchQuery({
        queryKey: logContextKey(muscle, exercise, date),
        queryFn: ({ signal }) => fetchLogContext(muscle, exercise, date, signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
}

/** Shared invalidation after any manage-element action (rename/delete/hide). */
function invalidateElementLists(qc: QueryClient): void {
    void qc.invalidateQueries({ queryKey: ["muscles"] });
    void qc.invalidateQueries({ queryKey: ["analytics", "top-muscles"] });
    void qc.invalidateQueries({ queryKey: ["analytics", "top-exercises"] });
    // Invalidate all hidden-exercise caches so the "Show Hidden" expander appears
    // immediately after hiding an exercise (GYM-104 #2: the expander was invisible
    // because the hidden-exercises cache was not cleared after hide/unhide/move ops).
    void qc.invalidateQueries({ queryKey: ["exercises", "hidden"] });
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
                queryKey: ["analytics", "exercise-progress"],
            });
            void qc.invalidateQueries({
                queryKey: ["analytics", "top-exercises", vars.muscleName],
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
                queryKey: ["analytics", "exercise-progress"],
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
                queryKey: ["analytics", "exercise-progress"],
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
        queryKey: ["muscles", "hidden"],
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
        queryKey: ["exercises", "hidden", muscleName],
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
            void qc.invalidateQueries({ queryKey: ["muscles"] });
            void qc.invalidateQueries({ queryKey: ["analytics", "top-muscles"] });
            void qc.invalidateQueries({ queryKey: ["muscles", "hidden"] });
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
            void qc.invalidateQueries({ queryKey: ["muscles"] });
            void qc.invalidateQueries({ queryKey: ["analytics", "top-muscles"] });
            void qc.invalidateQueries({ queryKey: ["analytics", "top-exercises"] });
            void qc.invalidateQueries({ queryKey: ["exercises", "hidden", vars.muscleName] });
        },
    });
}

// ── GYM-94: Exercise search (ADR 0003 Channel B) ─────────────────────────────

/** Re-export for consumers (ExerciseSearchField). */
export type { ExerciseCandidate };

/**
 * GET /exercises/search — debounced ranked candidate hook for the
 * search-and-pick dropdown (GYM-94).
 *
 * Fires only when `q` is non-empty (after trim) and `muscleId` is present,
 * so the query is always scoped and never fans out on the empty path (ARCH §2).
 * Short staleTime (30 s) so typing produces fresh results; gcTime kept short
 * so stale candidate arrays don't accumulate in memory mid-session.
 *
 * @param q - the debounced search query (raw user input, trimmed by the hook).
 * @param muscleId - numeric id of the selected muscle (scope required for GYM-94).
 * @param lang - resolved locale code from getLocale() / useLocale() (GYM-108).
 * @param limit - max candidates to return (default 8 for the dropdown).
 */
export function useExerciseSearch(
    q: string,
    muscleId: number | null,
    lang: string,
    limit = 8,
) {
    const trimmed = q.trim();
    return useQuery<ExerciseCandidate[]>({
        queryKey: ["exercises", "search", muscleId, lang, trimmed, limit],
        queryFn: ({ signal }) =>
            searchExercises(trimmed, muscleId ?? undefined, lang, limit, signal),
        enabled: trimmed.length > 0 && muscleId !== null,
        staleTime: 30_000,
        gcTime: 60_000,
        // Avoid flashing a stale list for a new query — keep previous data visible
        // as a placeholder while the fresh request is in-flight.
        placeholderData: (prev) => prev,
    });
}
