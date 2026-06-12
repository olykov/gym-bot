/**
 * Read-side data model for the record picker (GYM-127, extracted from
 * RecordPicker.tsx): every query the picker consumes plus the pure
 * derivations on top of them. RecordPicker stays the orchestrator (UI state,
 * mutations, handlers); this hook owns "what is there to show".
 *
 * Derivations preserved verbatim from the original component:
 *  - muscleByName / selectedMuscleId — name→Muscle lookup for the catalog.
 *  - exerciseList — full catalog (GYM-83) ordered by top-exercises frequency
 *    desc, then alpha; never-logged exercises sort last.
 *  - muscleOptions — visible muscles ONLY (GYM-103: hidden never linger),
 *    ordered by top-muscles frequency desc, then alpha.
 *  - ownedExerciseIds — visible ∪ hidden ids for the GYM-114 search marks.
 *  - continueExercise — the group whose set has the highest training_id (the
 *    most recently logged today), with a first-group fallback.
 *
 * Prefetches (§12.5 perf) also live here: picker reads warm on mount, and the
 * Continue exercise's log-context warms as soon as it is derived.
 */
import { useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
    useMuscles,
    useTopMuscles,
    useTopExercises,
    useExercises,
} from "@/hooks/useAnalytics";
import { useTrainingDay } from "@/hooks/useTraining";
import {
    useHiddenMuscles,
    useHiddenExercises,
    prefetchPickerReads,
    prefetchLogContext,
} from "@/hooks/useRecord";
import type { Muscle, Exercise } from "@/api/analytics";
import type { ContinueExercise } from "./MusclePanel";

/**
 * All read-side picker data, derived for one (today, selectedMuscle) pair.
 *
 * @param today - today's date (YYYY-MM-DD), the day/log-context key.
 * @param selectedMuscle - the controlled selected muscle name (null on the
 *   muscle step) — scopes the exercise reads.
 */
export function usePickerData(today: string, selectedMuscle: string | null) {
    const qc = useQueryClient();
    const topMuscles = useTopMuscles();
    const muscles = useMuscles();
    const day = useTrainingDay(today);

    // GYM-83: frequency data (top-exercises) is kept for ordering only.
    const topExercises = useTopExercises(selectedMuscle);

    // GYM-103: hidden lists for the "Show Hidden" expander.
    const hiddenMuscles = useHiddenMuscles();
    const hiddenExercises = useHiddenExercises(selectedMuscle);

    // Full muscle catalog (Muscle[] with id + is_mine) — keyed by name for lookup.
    const muscleByName = useMemo((): Map<string, Muscle> => {
        const map = new Map<string, Muscle>();
        for (const m of muscles.data ?? []) {
            map.set(m.name, m);
        }
        return map;
    }, [muscles.data]);

    // Derive the selected muscle's numeric id (to fetch full exercises with is_mine).
    const selectedMuscleId = useMemo((): number | null => {
        if (!selectedMuscle) return null;
        return muscleByName.get(selectedMuscle)?.id ?? null;
    }, [selectedMuscle, muscleByName]);

    // GYM-83: full catalog for the selected muscle (Exercise[] with id + is_mine).
    // This is now the tile source. top-exercises provides frequency for ordering only.
    const fullExercises = useExercises(selectedMuscleId);

    // GYM-114: set of exercise ids the user already owns for this muscle.
    // Union of VISIBLE exercises (fullExercises) + HIDDEN exercises (hiddenExercises)
    // so the search dropdown can mark already-owned candidates. Both queries are
    // already live on the exercise step (no new requests needed).
    const ownedExerciseIds = useMemo((): Set<number> => {
        const ids = new Set<number>();
        for (const ex of fullExercises.data ?? []) {
            ids.add(ex.id);
        }
        for (const ex of hiddenExercises.data ?? []) {
            ids.add(ex.id);
        }
        return ids;
    }, [fullExercises.data, hiddenExercises.data]);

    // GYM-83: frequency map (exercise name → frequency) built from top-exercises.
    const frequencyMap = useMemo((): Map<string, number> => {
        const map = new Map<string, number>();
        for (const ex of topExercises.data ?? []) {
            map.set(ex.name, ex.frequency);
        }
        return map;
    }, [topExercises.data]);

    // GYM-83: sorted exercise list — full catalog ordered by frequency desc, then alpha.
    // Never-logged exercises get frequency 0 and sort after trained ones.
    const exerciseList = useMemo((): Exercise[] => {
        const catalog = fullExercises.data ?? [];
        return [...catalog].sort((a, b) => {
            const fa = frequencyMap.get(a.name) ?? 0;
            const fb = frequencyMap.get(b.name) ?? 0;
            if (fb !== fa) return fb - fa;
            return a.name.localeCompare(b.name);
        });
    }, [fullExercises.data, frequencyMap]);

    // Warm the picker reads + the Continue exercise's log-context on open (§12.5).
    useEffect(() => {
        prefetchPickerReads(qc, today);
    }, [qc, today]);

    // Continue = the exercise group whose set has the highest training_id
    // (the most recently logged today). training_id is a serial id, so the
    // largest value is the latest insert. Falls back to string compare.
    const continueExercise: ContinueExercise | null = useMemo(() => {
        const exs = day.data?.exercises ?? [];
        if (exs.length === 0) return null;
        let best: ContinueExercise | null = null;
        let bestKey = -Infinity;
        for (const ex of exs) {
            for (const s of ex.sets) {
                const k = Number(s.training_id);
                const key = Number.isFinite(k) ? k : -Infinity;
                if (key > bestKey) {
                    bestKey = key;
                    best = {
                        muscleName: ex.muscle_name,
                        exerciseName: ex.exercise_name,
                    };
                }
            }
        }
        // No finite id anywhere → fall back to first appearance (alpha order).
        if (!best && exs[0]) {
            best = {
                muscleName: exs[0].muscle_name,
                exerciseName: exs[0].exercise_name,
            };
        }
        return best;
    }, [day.data]);

    // Prefetch the Continue exercise's log-context so tapping it is instant.
    useEffect(() => {
        if (continueExercise) {
            prefetchLogContext(
                qc,
                continueExercise.muscleName,
                continueExercise.exerciseName,
                today,
            );
        }
    }, [qc, continueExercise, today]);

    // GYM-103 fix: muscle tiles come ONLY from the VISIBLE muscles list (which
    // already excludes hidden after GYM-99). top-muscles is used SOLELY for
    // ordering (frequency map). A hidden muscle therefore never lingers as a tile
    // — even if it still appears in top-muscles (which ignores hidden status).
    // This mirrors what GYM-83 did for exercises.
    const muscleFrequencyMap = useMemo((): Map<string, number> => {
        const map = new Map<string, number>();
        for (const m of topMuscles.data ?? []) {
            map.set(m.name, m.frequency);
        }
        return map;
    }, [topMuscles.data]);

    const muscleOptions = useMemo((): string[] => {
        const catalog = muscles.data ?? [];
        return [...catalog]
            .sort((a, b) => {
                const fa = muscleFrequencyMap.get(a.name) ?? 0;
                const fb = muscleFrequencyMap.get(b.name) ?? 0;
                if (fb !== fa) return fb - fa;
                return a.name.localeCompare(b.name);
            })
            .map((m) => m.name);
    }, [muscles.data, muscleFrequencyMap]);

    return {
        muscles,
        day,
        hiddenMuscles,
        hiddenExercises,
        fullExercises,
        muscleByName,
        selectedMuscleId,
        ownedExerciseIds,
        exerciseList,
        continueExercise,
        muscleOptions,
    };
}
