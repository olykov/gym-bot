/**
 * Utility functions for URL encoding/decoding of muscle and exercise names
 */

/**
 * Encode a muscle or exercise name for URL use
 * Converts spaces to hyphens and handles special characters
 */
export function encodeForUrl(name: string): string {
  return name
    .trim()
    .replace(/\s+/g, '-') // Replace spaces with hyphens
    .replace(/[^a-zA-Z0-9\-]/g, '') // Remove special characters except hyphens
    .toLowerCase();
}

/**
 * Decode a URL segment back to original name format
 * Converts hyphens back to spaces and capitalizes appropriately
 */
export function decodeFromUrl(urlSegment: string): string {
  return urlSegment
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Generate a direct link to a specific exercise
 */
export function generateExerciseUrl(muscle: string, exercise: string, baseUrl?: string): string {
  const base = baseUrl || (typeof window !== 'undefined' ? window.location.origin : '');
  const encodedMuscle = encodeForUrl(muscle);
  const encodedExercise = encodeForUrl(exercise);
  
  return `${base}/exercises/${encodedMuscle}/${encodedExercise}`;
}

/**
 * Validate that a decoded muscle/exercise combination exists in user's data
 */
export function validateExerciseParams(
  muscle: string, 
  exercise: string, 
  userMuscles: Array<{ name: string; exercises: string[] }>
): boolean {
  const muscleGroup = userMuscles.find(m => m.name.toLowerCase() === muscle.toLowerCase());
  if (!muscleGroup) return false;
  
  return muscleGroup.exercises.some(e => e.toLowerCase() === exercise.toLowerCase());
}