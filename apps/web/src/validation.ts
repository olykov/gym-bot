/**
 * Client-side input limits mirroring the API validation rules (GYM-77 #2).
 *
 * The SERVER is authoritative — these constants exist for immediate UX only
 * (maxLength on inputs, disable submit when empty after trim). If the API still
 * returns a 422, the error message is surfaced gracefully by the caller.
 *
 * Source of truth for the server-side limits: docs/validation.md (GYM-75).
 * Keep these in sync with the API contract when the limits change.
 */

/** Maximum character length for a muscle name (mirrors API validation). */
export const MUSCLE_NAME_MAX = 30;

/** Maximum character length for an exercise name (mirrors API validation). */
export const EXERCISE_NAME_MAX = 40;

/**
 * Weight stepper increment in kg — gym-plate granularity (spec §11.4).
 * Single source for the three steppers (SetLogger, SetEditor, AddSetInline);
 * GYM-126 owns any further constant dedup.
 */
export const WEIGHT_STEP = 2.5;
