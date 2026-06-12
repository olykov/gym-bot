/**
 * Catalog access layer — GYM-109 (ADR 0003 Channel A). No i18n library:
 * `t()` / `tPlural()` resolve the typed catalog in messages.ts against the
 * GYM-108 locale (getLocale / useLocale).
 *
 * Usage:
 *  - Components: `const { t, tp, muscle } = useT();` (locale-bound, memoised).
 *  - Pure modules (derive.ts, date helpers): import `t` / `tPlural` /
 *    `localizeMuscleName` directly — they read getLocale() per call, or take
 *    an explicit `locale` for deterministic tests.
 *
 * Interpolation: `{name}`-style placeholders, params as string | number.
 * Unknown placeholders are left verbatim (fail-soft; typos surface visibly).
 *
 * Plurals: `plural(n, forms, locale)` picks the Intl.PluralRules category
 * (en: one/other; ru: one/few/many/other) and `tPlural` interpolates `{n}`.
 */
import { useMemo } from "react";
import type { Locale } from "@/i18n/locales";
import { getLocale, useLocale } from "@/i18n/locale";
import {
    MESSAGES,
    PLURALS,
    type MessageKey,
    type PluralForms,
    type PluralKey,
} from "@/i18n/messages";

export type { MessageKey, PluralKey } from "@/i18n/messages";

/** Interpolation params: `{name}` placeholders → string/number values. */
export type MessageParams = Record<string, string | number>;

/** Replace `{name}` tokens; unknown tokens stay verbatim (visible typo). */
function interpolate(template: string, params?: MessageParams): string {
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, (token, name: string) => {
        const value = params[name];
        return value === undefined ? token : String(value);
    });
}

/** Pure core: resolve a message for an explicit locale (tests use this). */
export function translate(
    locale: Locale,
    key: MessageKey,
    params?: MessageParams,
): string {
    return interpolate(MESSAGES[key][locale], params);
}

/** Resolve a message for the active Telegram locale. */
export function t(key: MessageKey, params?: MessageParams): string {
    return translate(getLocale(), key, params);
}

// Intl.PluralRules instances are cheap but not free — cache one per locale.
const pluralRulesCache = new Map<Locale, Intl.PluralRules>();

function pluralRules(locale: Locale): Intl.PluralRules {
    let rules = pluralRulesCache.get(locale);
    if (!rules) {
        rules = new Intl.PluralRules(locale);
        pluralRulesCache.set(locale, rules);
    }
    return rules;
}

/**
 * Pick the right plural form for `n` in `locale` via Intl.PluralRules.
 * Missing categories fall back to `other` (always present by type).
 */
export function plural(n: number, forms: PluralForms, locale: Locale): string {
    const category = pluralRules(locale).select(n);
    const form =
        category === "one" || category === "few" || category === "many"
            ? (forms[category] ?? forms.other)
            : forms.other;
    return form;
}

/** Pure core: countable message for an explicit locale ("3 сета" etc.). */
export function translatePlural(
    locale: Locale,
    key: PluralKey,
    n: number,
): string {
    return interpolate(plural(n, PLURALS[key][locale], locale), { n });
}

/** Countable message for the active Telegram locale. */
export function tPlural(key: PluralKey, n: number): string {
    return translatePlural(getLocale(), key, n);
}

// ── Muscle labels (ADR 0003: the 8 fixed muscles localize HERE) ─────────────

/** Canonical API muscle name (lowercased) → its catalog key. */
const MUSCLE_KEY_BY_NAME: Record<string, MessageKey> = {
    abs: "muscles.abs",
    back: "muscles.back",
    biceps: "muscles.biceps",
    chest: "muscles.chest",
    forearms: "muscles.forearms",
    legs: "muscles.legs",
    shoulders: "muscles.shoulders",
    triceps: "muscles.triceps",
};

/**
 * Localize a canonical muscle name for display. The API keeps returning the
 * canonical English name (it stays the query/mutation key); only the visible
 * label changes. Unknown / user-created muscle names pass through unchanged.
 */
export function localizeMuscleName(
    name: string,
    locale: Locale = getLocale(),
): string {
    const key = MUSCLE_KEY_BY_NAME[name.trim().toLowerCase()];
    return key ? translate(locale, key) : name;
}

// ── React hook ───────────────────────────────────────────────────────────────

/** Locale-bound translator handed out by useT(). */
export interface Translator {
    locale: Locale;
    /** Message lookup with `{name}` interpolation. */
    t: (key: MessageKey, params?: MessageParams) => string;
    /** Countable message ("3 sets" / "3 сета"). */
    tp: (key: PluralKey, n: number) => string;
    /** Display label for a (possibly canonical) muscle name. */
    muscle: (name: string) => string;
}

/**
 * The component-side entry point: a translator bound to the session locale.
 * Memoised once (the locale never changes mid-session, see useLocale).
 */
export function useT(): Translator {
    const locale = useLocale();
    return useMemo(
        () => ({
            locale,
            t: (key, params) => translate(locale, key, params),
            tp: (key, n) => translatePlural(locale, key, n),
            muscle: (name) => localizeMuscleName(name, locale),
        }),
        [locale],
    );
}
