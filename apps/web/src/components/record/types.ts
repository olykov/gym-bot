/**
 * Shared types for the record-training flow (spec §12).
 *
 * The chosen exercise is just its identity — Phase B derives every pre-fill
 * value from `GET /analytics/log-context` (last-session sets), so no weight/reps
 * are carried across the pick anymore (GYM-72).
 */

/** The exercise the user picked in Phase A, handed to Phase B (the logger). */
export interface ChosenExercise {
    muscleName: string;
    exerciseName: string;
}
