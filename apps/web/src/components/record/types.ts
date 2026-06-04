/**
 * Shared types for the record-training flow (spec §12). The chosen exercise
 * carries the optional last working set carried from the fast-lane chip so
 * Phase B can pre-fill instantly without a network round-trip (spec §12.3).
 */

/** The exercise the user picked in Phase A, handed to Phase B (the logger). */
export interface ChosenExercise {
    muscleName: string;
    exerciseName: string;
    /** Last working-set weight from `recent-exercises`, when the pick came from
     *  the fast lane (carried for the instant cold-open pre-fill). */
    lastWeight?: number | null;
    /** Last working-set reps from `recent-exercises` (see lastWeight). */
    lastReps?: number | null;
}
