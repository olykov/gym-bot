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
    fetchLogContext,
    fetchTopExercises,
    fetchTopMuscles,
    type Exercise,
    type ExerciseCreate,
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
 * nothing. A long staleTime keeps a re-entered exercise instant; a save
 * invalidates this key so the recap/auto-set stay correct.
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
        onSuccess: (_data, vars) => {
            void qc.invalidateQueries({ queryKey: ["muscles"] });
            void qc.invalidateQueries({
                queryKey: ["analytics", "top-exercises", vars.muscle_name],
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
 * tiles appear instantly. Same key/shape as useTopExercises.
 */
export function prefetchMuscleExercises(qc: QueryClient, muscle: string): void {
    void qc.prefetchQuery({
        queryKey: ["analytics", "top-exercises", muscle, TOP_EXERCISES_LIMIT],
        queryFn: ({ signal }) =>
            fetchTopExercises(muscle, TOP_EXERCISES_LIMIT, signal),
        staleTime: SESSION_STALE,
        gcTime: SESSION_GC,
    });
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
