/**
 * Telegram themeParams -> CSS variables (spec §3 / §9.3).
 *
 * Telegram owns the base surface/text palette; we mirror its values onto the
 * CSS vars consumed by Tailwind and components. The app-owned brand layer
 * (--accent*, grid ramp) is NOT touched here — it lives in tokens.css and only
 * flips via the data-theme attribute we set from Telegram's colorScheme.
 */
import type { ThemeParams } from "@twa-dev/types";

type ThemeKey = keyof ThemeParams;

/** Telegram themeParams key -> our CSS variable. */
const THEME_MAP: Partial<Record<ThemeKey, string>> = {
    bg_color: "--bg",
    text_color: "--text",
    hint_color: "--hint",
    link_color: "--link",
    button_color: "--button",
    button_text_color: "--button-text",
    secondary_bg_color: "--secondary-bg",
};

/**
 * Apply Telegram themeParams to the document root and set the light/dark flag.
 *
 * @param params - Telegram themeParams (may be partial outside Telegram).
 * @param colorScheme - "light" | "dark" reported by Telegram, if known.
 */
export function applyTelegramTheme(
    params: ThemeParams | undefined,
    colorScheme: "light" | "dark" | undefined,
): void {
    const root = document.documentElement;

    if (colorScheme === "light" || colorScheme === "dark") {
        root.setAttribute("data-theme", colorScheme);
    }

    if (!params) return;

    for (const [tgKey, cssVar] of Object.entries(THEME_MAP)) {
        if (!cssVar) continue;
        const value = params[tgKey as ThemeKey];
        if (typeof value === "string" && value) {
            root.style.setProperty(cssVar, value);
        }
    }
}
