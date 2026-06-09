/**
 * Supported-locales registry — single source of truth for GYM-108.
 *
 * This is the ONLY place that lists which locales exist. UI catalogs (GYM-109)
 * and DB alias seeds (GYM-92) must reference these codes; they never maintain
 * their own locale lists. See ADR 0003.
 */

/** All supported ISO-639-1 locale codes. */
export const SUPPORTED_LOCALES = ["en", "ru"] as const;

/** Union type of every supported locale code. */
export type Locale = (typeof SUPPORTED_LOCALES)[number];

/** Fallback locale when Telegram language_code is missing or not supported. */
export const DEFAULT_LOCALE: Locale = "en";
