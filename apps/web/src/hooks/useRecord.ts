/**
 * TanStack Query hooks for the record-training flow (spec §12) — mirrors
 * useAnalytics.ts / useTraining.ts. Picker reads (recent-exercises,
 * completed-sets, personal-record), the catalog create mutations
 * (muscle/exercise add-inline), and the `POST /training` mutation that logs a
 * set and fans out the §12.5 cross-screen invalidation so Dashboard / Progress
 * / History never go stale after a save.
 *
 * Every read fires ONLY when the sheet needs it: recent-exercises is enabled by
 * the caller (the sheet open), and the per-exercise reads stay disabled until an
 * exercise is chosen — the empty path fires nothing (ARCH §2).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    createExercise,
    createMuscle,
    fetchCompletedSets,
    fetchPersonalRecord,
    fetchRecentExercises,
    type CompletedSets,
    type Exercise,
    type ExerciseCreate,
    type Muscle,
    type MuscleCreate,
    type PersonalRecord,
    type RecentExercise,
} from "@/api/analytics";
import {
    createTraining,
    type Training,
    type TrainingCreate,
} from "@/api/training";

/** Fast-lane size: the user's last-trained exercises shown as 1-tap chips. */
export const RECENT_EXERCISES_LIMIT = 8;

/**
 * The fast lane — the caller's most-recently-trained exercises (spec §12.2).
 * `enabled` lets the sheet defer the read until it opens (never on app mount).
 */
export function useRecentExercises(enabled: boolean) {
    return useQuery<RecentExercise[]>({
        queryKey: ["analytics", "recent-exercises"],
        queryFn: ({ signal }) =>
            fetchRecentExercises(RECENT_EXERCISES_LIMIT, signal),
        enabled,
        staleTime: 60_000,
    });
}

/**
 * Set numbers already recorded for an exercise on `date` (auto set #, §12.3).
 * Disabled until both names exist, so Phase A fires nothing.
 */
export function useCompletedSets(
    muscle: string | null,
    exercise: string | null,
    date: string,
) {
    return useQuery<CompletedSets>({
        queryKey: ["analytics", "completed-sets", muscle, exercise, date],
        queryFn: ({ signal }) =>
            fetchCompletedSets(muscle as string, exercise as string, date, signal),
        enabled: Boolean(muscle && exercise),
        // Today's sets change as we log; keep it short so a fresh sheet is right.
        staleTime: 0,
    });
}

/**
 * The PR target / cold-open pre-fill fallback (§12.3). Disabled until both
 * names exist. `null` means no history — first save becomes the PR.
 */
export function usePersonalRecord(
    muscle: string | null,
    exercise: string | null,
) {
    return useQuery<PersonalRecord | null>({
        queryKey: ["analytics", "personal-record", muscle, exercise],
        queryFn: ({ signal }) =>
            fetchPersonalRecord(muscle as string, exercise as string, signal),
        enabled: Boolean(muscle && exercise),
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
 * today's History day, AND recency (the fast lane), so every one of those keys
 * is invalidated. `today` is the day-detail key to refresh.
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
                    "completed-sets",
                    vars.muscle_name,
                    vars.exercise_name,
                ],
            });
            void qc.invalidateQueries({
                queryKey: [
                    "analytics",
                    "personal-record",
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
            void qc.invalidateQueries({
                queryKey: ["analytics", "recent-exercises"],
            });
        },
    });
}
