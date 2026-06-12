/**
 * Unit tests for deriveContinueExercise (GYM-139).
 *
 * Root cause: training_id is a uuid4().hex string (32 lower-case hex chars),
 * not a numeric serial. The old derivation called Number(training_id) which
 * always produced NaN — the Continue tile therefore always fell back to exs[0]
 * (alphabetically first exercise) regardless of what was most recently logged.
 *
 * These tests encode the two correctness invariants:
 *  1. Session override: when lastLoggedExercise is provided AND the exercise
 *     is in today's data, deriveContinueExercise returns it — not exs[0].
 *  2. Fallback: when no override is given (fresh open), the first exercise in
 *     the server array is returned (server orders by e.name, so this is
 *     deterministic — it's the pre-fix behaviour and is acceptable for the
 *     cross-session case where no server-side ordering by recency exists yet).
 *
 * Reproduce the original bug: log Abdominal Curl (exs[0] alphabetically),
 * then log Bench Press. The old code returned Abdominal Curl even with Bench
 * Press in the data and Bench Press as lastLoggedExercise.
 */
import { describe, expect, it } from "vitest";
import { deriveContinueExercise } from "./usePickerData";
import type { TrainingDayExercise } from "@/api/training";
import type { ContinueExercise } from "./MusclePanel";

/** Build a minimal TrainingDayExercise with uuid training_ids (the real schema). */
function mkExercise(
    exerciseName: string,
    muscleName: string,
    setCount = 1,
): TrainingDayExercise {
    return {
        exercise_id: Math.floor(Math.random() * 1000),
        exercise_name: exerciseName,
        muscle_name: muscleName,
        sets: Array.from({ length: setCount }, (_, i) => ({
            // Real training_id is a uuid4().hex — not a number.
            training_id: `a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d${i}`,
            set: i + 1,
            weight: 60,
            reps: 10,
            // GYM-141: is_pr defaults false in test fixtures.
            is_pr: false,
        })),
    };
}

describe("deriveContinueExercise", () => {
    it("returns null when there are no exercises today", () => {
        expect(deriveContinueExercise([], null)).toBeNull();
        expect(deriveContinueExercise([], { muscleName: "Chest", exerciseName: "Bench Press" })).toBeNull();
    });

    it("falls back to exs[0] when no session override is given (fresh open)", () => {
        const exs = [
            mkExercise("Abdominal Curl", "Abs"),
            mkExercise("Bench Press", "Chest"),
        ];
        const result = deriveContinueExercise(exs, null);
        expect(result).toEqual({ muscleName: "Abs", exerciseName: "Abdominal Curl" });
    });

    it("uses the session override when the exercise is in today's data", () => {
        // This is the GYM-139 scenario: Abdominal Curl is exs[0] (alphabetical),
        // but the user just logged Bench Press — Continue must show Bench Press.
        const exs = [
            mkExercise("Abdominal Curl", "Abs"),
            mkExercise("Bench Press", "Chest"),
        ];
        const override: ContinueExercise = { muscleName: "Chest", exerciseName: "Bench Press" };
        const result = deriveContinueExercise(exs, override);
        expect(result).toEqual({ muscleName: "Chest", exerciseName: "Bench Press" });
    });

    it("falls back to exs[0] when the override exercise is NOT in today's data", () => {
        // Override references an exercise not present in the day — e.g. the
        // user switched to a different muscle group. Fall back gracefully.
        const exs = [mkExercise("Abdominal Curl", "Abs")];
        const override: ContinueExercise = { muscleName: "Legs", exerciseName: "Squat" };
        const result = deriveContinueExercise(exs, override);
        expect(result).toEqual({ muscleName: "Abs", exerciseName: "Abdominal Curl" });
    });

    it("matches override by BOTH muscleName AND exerciseName (same exercise name, different muscle)", () => {
        // Edge case: two muscles could theoretically have exercises with the same name.
        const exs = [
            mkExercise("Press", "Chest"),
            mkExercise("Press", "Shoulders"),
        ];
        const override: ContinueExercise = { muscleName: "Shoulders", exerciseName: "Press" };
        const result = deriveContinueExercise(exs, override);
        expect(result).toEqual({ muscleName: "Shoulders", exerciseName: "Press" });
    });

    it("works with uuid training_ids (does not depend on numeric ordering)", () => {
        // Verify the fix: uuid training_ids must NOT affect which exercise is chosen.
        // If the old Number(training_id) logic were still in place, all keys would
        // be -Infinity and the result would always be exs[0].
        const exs = [
            {
                exercise_id: 1,
                exercise_name: "Abdominal Curl",
                muscle_name: "Abs",
                sets: [
                    { training_id: "ffffffffffffffffffffffffffffffff", set: 1, weight: 50, reps: 12, is_pr: false },
                ],
            },
            {
                exercise_id: 2,
                exercise_name: "Bench Press",
                muscle_name: "Chest",
                sets: [
                    { training_id: "00000000000000000000000000000000", set: 1, weight: 80, reps: 5, is_pr: false },
                ],
            },
        ];
        // Without an override, still returns exs[0] (Abdominal Curl) regardless of
        // how training_ids compare — uuid ordering is not used.
        expect(deriveContinueExercise(exs, null)).toEqual({
            muscleName: "Abs",
            exerciseName: "Abdominal Curl",
        });
        // With the correct override (Bench Press was logged last), returns Bench Press.
        expect(deriveContinueExercise(exs, { muscleName: "Chest", exerciseName: "Bench Press" })).toEqual({
            muscleName: "Chest",
            exerciseName: "Bench Press",
        });
    });

    it("handles a single exercise: override matching it is returned", () => {
        const exs = [mkExercise("Deadlift", "Back", 3)];
        const override: ContinueExercise = { muscleName: "Back", exerciseName: "Deadlift" };
        expect(deriveContinueExercise(exs, override)).toEqual({ muscleName: "Back", exerciseName: "Deadlift" });
    });

    it("handles a single exercise: no override returns the only exercise", () => {
        const exs = [mkExercise("Deadlift", "Back", 3)];
        expect(deriveContinueExercise(exs, null)).toEqual({ muscleName: "Back", exerciseName: "Deadlift" });
    });
});
