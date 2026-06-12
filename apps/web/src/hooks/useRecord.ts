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
    fetchExercises,
    fetchExerciseTrend,
    fetchLogContext,
    fetchTopExercises,
    fetchTopMuscles,
    searchExercises,
    type Exercise,
    type ExerciseCandidate,
    type ExerciseCreate,
    type ExerciseTrend,
    type LogContext,
    type Muscle,
    type MuscleCreate,
} from "@/api/analytics";
import { fetchTrainingDay } from "@/api/training";
import {
    createTraining,
    type Training,
    type TrainingCreate,
} from "@/api/training";
import { queryKeys } from "@/api/queryKeys";

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

/**
 * Query key for one exercise's log-context on a date — re-exported from the
 * central queryKeys factory (GYM-126) so existing imports keep working.
 */
export const logContextKey = queryKeys.analytics.logContext;

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

/** Trailing window (weeks) for the SetLogger e1RM trend sparkline (GYM-135). */
export const TREND_WEEKS = 8;

/**
 * GYM-135: the e1RM trend feeding the SetLogger sparkline + trend chip
 * (`GET /analytics/exercise-trend`, GYM-134). Mounted only inside Phase B
 * (TrendSparkline), so it fires alongside log-context on entry and never
 * delays stepper interactivity — the steppers render independently of it.
 * Normal SESSION staleTime: a save invalidates `exerciseTrendPrefix`, which
 * marks the key stale and refetches the active query regardless of staleTime.
 */
export function useExerciseTrend(
    muscle: string | null,
    exercise: string | null,
) {
    return useQuery<ExerciseTrend>({
        queryKey: queryKeys.analytics.exerciseTrend(
            muscle,
            exercise,
            TREND_WEEKS,
        ),
        queryFn: ({ signal }) =>
            fetchExerciseTrend(
                muscle as string,
                exercise as string,
                TREND_WEEKS,
                signal,
            ),
        enabled: Boolean(muscle && exercise),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
}

/** Add-inline: create a private muscle, then refresh the muscle catalog. */
export function useCreateMuscle() {
    const qc = useQueryClient();
    return useMutation<Muscle, Error, MuscleCreate>({
        mutationFn: (body) => createMuscle(body),
        onSuccess: () => {
            void qc.invalidateQueries({ queryKey: queryKeys.muscles.list });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topMuscles,
            });
        },
    });
}

/** Add-inline: create a private exercise under a muscle name, then refresh. */
export function useCreateExercise() {
    const qc = useQueryClient();
    return useMutation<Exercise, Error, ExerciseCreate>({
        mutationFn: (body) => createExercise(body),
        onSuccess: (data, vars) => {
            void qc.invalidateQueries({ queryKey: queryKeys.muscles.list });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.topExercisesPrefix(
                    vars.muscle_name,
                ),
            });
            // GYM-100 fix #3: after add→resolve (resolution=existing or resolution=unhidden),
            // the GYM-99 server now correctly returns the exercise's real PR/history instead
            // of a cached empty context. Invalidate the log-context for the resolved exercise
            // (by muscle+exercise prefix, covering all dates) so SetLogger re-fetches instead
            // of serving a 10-min-stale empty result. Use the canonical name the backend
            // returned (data.name), not the user-typed name, since the resolution may have
            // matched a differently-cased or trimmed name.
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.logContextPrefix(
                    vars.muscle_name,
                    data.name,
                ),
            });
            // Also invalidate exercise-progress for the canonical name so the Progress chart
            // is not stale if the user re-adds a previously tracked exercise.
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseProgressPrefix(
                    vars.muscle_name,
                    data.name,
                ),
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
 *
 * GYM-125 #2: invalidation deliberately runs in `onSettled` (NOT onSuccess) —
 * a 409 set-number collision must also refetch the log-context so the caller's
 * `computeNextSet` auto-corrects to a free set number. Do not narrow this to
 * the success path.
 */
export function useCreateTraining(today: string) {
    const qc = useQueryClient();
    return useMutation<Training, Error, TrainingCreate>({
        mutationFn: (body) => createTraining(body),
        onSettled: (_data, _err, vars) => {
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.summaryPrefix,
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.activityPrefix,
            });
            // GYM-136: a saved set moves this week's totals on the Dashboard.
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.weekComparePrefix,
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.logContextPrefix(
                    vars.muscle_name,
                    vars.exercise_name,
                ),
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseProgressPrefix(
                    vars.muscle_name,
                    vars.exercise_name,
                ),
            });
            // GYM-135: a saved set changes the e1RM trend (and session volume),
            // so the sparkline must refetch on the next render/mount.
            void qc.invalidateQueries({
                queryKey: queryKeys.analytics.exerciseTrendPrefix(
                    vars.muscle_name,
                    vars.exercise_name,
                ),
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.training.daysPrefix,
            });
            void qc.invalidateQueries({
                queryKey: queryKeys.training.day(today),
            });
        },
    });
}

/**
 * Warm the picker reads on sheet open (spec §12.5 perf): the muscle tiles
 * (`top-muscles`) and today's training (the Continue tile). Long staleTime for
 * top-muscles (frequency data is stable mid-session). The day key uses staleTime:0
 * so it always re-fetches — this is belt-and-suspenders with the useTrainingDay
 * refetchOnMount:'always' fix (GYM-115): the prefetch staleTime can never shadow
 * invalidated day data and cause the Continue tile to show a stale exercise.
 */
export function prefetchPickerReads(qc: QueryClient, today: string): void {
    void qc.prefetchQuery({
        queryKey: queryKeys.analytics.topMuscles,
        queryFn: ({ signal }) => fetchTopMuscles(signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
    void qc.prefetchQuery({
        queryKey: queryKeys.training.day(today),
        queryFn: ({ signal }) => fetchTrainingDay(today, signal),
        staleTime: 0,
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
        queryKey: queryKeys.analytics.topExercises(muscle, TOP_EXERCISES_LIMIT),
        queryFn: ({ signal }) =>
            fetchTopExercises(muscle, TOP_EXERCISES_LIMIT, signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
    if (muscleId != null) {
        void qc.prefetchQuery({
            queryKey: queryKeys.muscles.exercises(muscleId),
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

// ── Manage-element hooks (GYM-82/90/99/103) ──────────────────────────────────
// Moved to useManageElements.ts in GYM-127 (file-size split, behavior
// identical). Re-exported here so existing import sites keep working.
export {
    useRenameMuscle,
    useDeleteMuscle,
    useHideMuscle,
    useRenameExercise,
    useDeleteExercise,
    useHideExercise,
    useMoveExercise,
    useHiddenMuscles,
    useHiddenExercises,
    useUnhideMuscle,
    useUnhideExercise,
} from "./useManageElements";

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
        queryKey: queryKeys.exercises.search(muscleId, lang, trimmed, limit),
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
