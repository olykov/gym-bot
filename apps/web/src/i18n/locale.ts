/**
 * Locale resolution — GYM-108 (ADR 0003 shared foundation).
 *
 * Reads Telegram language_code via the webapp accessor, normalises it
 * (lowercase, strip region tag: "ru-RU" → "ru"), maps to a supported locale,
 * and falls back to DEFAULT_LOCALE for anything unknown or missing.
 *
 * Public API for consumers:
 *   - `getLocale()` — pure util, no React, safe to call anywhere.
 *   - `useLocale()` — React hook; use inside components / other hooks.
 *
 * GYM-109 (UI string catalog) and GYM-93 (search API lang param) import from
 * here so the locale answer is always consistent.
 */
import { useMemo } from "react";
import { getTelegramLanguageCode } from "@/telegram/webapp";
import {
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    type Locale,
} from "@/i18n/locales";

/**
 * Normalise a raw Telegram language_code to an ISO-639-1 base code.
 *
 * Examples:
 *   "ru-RU" → "ru"
 *   "EN"    → "en"
 *   ""      → undefined
 */
function normalise(raw: string | undefined): string | undefined {
    if (!raw) return undefined;
    // Strip region suffix and lowercase ("ru-RU" → "ru", "EN" → "en").
    return raw.split("-")[0].toLowerCase();
}

/**
 * Return the active locale for the current Telegram user.
 *
 * Resolution chain:
 *   1. Read `WebApp.initDataUnsafe.user.language_code`.
 *   2. Normalise to ISO-639-1 base code.
 *   3. Check against SUPPORTED_LOCALES.
 *   4. Return DEFAULT_LOCALE ("en") for anything missing or unsupported.
 *
 * Safe to call outside Telegram (local dev / browser) — returns DEFAULT_LOCALE.
 */
export function getLocale(): Locale {
    const base = normalise(getTelegramLanguageCode());
    if (base && (SUPPORTED_LOCALES as readonly string[]).includes(base)) {
        return base as Locale;
    }
    return DEFAULT_LOCALE;
}

/**
 * React hook that returns the active locale.
 *
 * The locale is stable for the lifetime of the Mini App session (Telegram does
 * not hot-swap the language during a session), so the value is memoised with
 * an empty dependency array — no re-render on repeated calls.
 *
 * Usage:
 *   const locale = useLocale(); // "en" | "ru"
 */
export function useLocale(): Locale {
    // eslint-disable-next-line react-hooks/exhaustive-deps
    return useMemo(() => getLocale(), []);
}
