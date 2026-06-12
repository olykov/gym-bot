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
 *  - continueExercise — the most recently logged exercise today, derived via
 *    deriveContinueExercise (GYM-139).
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
import type { TrainingDayExercise } from "@/api/training";
import type { ContinueExercise } from "./MusclePanel";

/**
 * Derive the Continue tile exercise from today's server data and an optional
 * session-level override (GYM-139).
 *
 * Root cause fixed here: `training_id` is a uuid4().hex string (32 lower-case
 * hex characters). Comparing `Number(training_id)` always yields NaN, which
 * is not finite, so every set got key=-Infinity and `best` was never assigned.
 * The fallback then returned `exs[0]` — the alphabetically first exercise —
 * regardless of which was logged most recently.
 *
 * Fix strategy (two tiers):
 *  1. If `lastLoggedExercise` is provided (the exercise the user just logged
 *     in this session) AND it appears in today's server data, return it
 *     immediately. This covers the primary scenario: log exercise B, switch
 *     back to the picker — Continue must show B, not the alphabetically first.
 *  2. Otherwise fall back to `exs[0]` (the first exercise in the server
 *     response, ordered alphabetically by exercise name from the API). This is
 *     unchanged from the pre-bug-introduction behaviour and is "good enough"
 *     for fresh opens where no session override exists.
 *
 * Note: a server-side fix (ordering exercises by MAX(t.date) DESC so the API
 * response itself reflects insertion recency) would make tier-2 correct for
 * cross-session freshness too. That is core-api's domain (GYM-139 report).
 *
 * @param exercises - today's exercise groups from GET /training/day/{date}.
 * @param lastLoggedExercise - the exercise most recently logged in this session,
 *   or null when the sheet was just opened (no sets saved yet).
 * @returns The ContinueExercise to show, or null when nothing was trained today.
 */
export function deriveContinueExercise(
    exercises: TrainingDayExercise[],
    lastLoggedExercise: ContinueExercise | null,
): ContinueExercise | null {
    if (exercises.length === 0) return null;

    // Tier 1: session override — the exercise just logged wins if it's in today's data.
    if (lastLoggedExercise !== null) {
        const found = exercises.find(
            (ex) =>
                ex.muscle_name === lastLoggedExercise.muscleName &&
                ex.exercise_name === lastLoggedExercise.exerciseName,
        );
        if (found) {
            return {
                muscleName: found.muscle_name,
                exerciseName: found.exercise_name,
            };
        }
    }

    // Tier 2: no session override — fall back to first exercise (API returns
    // exercises ordered by e.name so this is deterministic).
    return {
        muscleName: exercises[0].muscle_name,
        exerciseName: exercises[0].exercise_name,
    };
}

/**
 * All read-side picker data, derived for one (today, selectedMuscle) pair.
 *
 * @param today - today's date (YYYY-MM-DD), the day/log-context key.
 * @param selectedMuscle - the controlled selected muscle name (null on the
 *   muscle step) — scopes the exercise reads.
 * @param lastLoggedExercise - the exercise most recently logged in this
 *   session (from RecordSheet's session log), used to override the Continue
 *   tile (GYM-139). Null on fresh opens.
 */
export function usePickerData(
    today: string,
    selectedMuscle: string | null,
    lastLoggedExercise: ContinueExercise | null = null,
) {
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

    // GYM-139: use deriveContinueExercise (pure function, tested) so the
    // session override wins over the broken Number(uuid) comparison.
    const continueExercise: ContinueExercise | null = useMemo(
        () => deriveContinueExercise(day.data?.exercises ?? [], lastLoggedExercise),
        [day.data, lastLoggedExercise],
    );

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
