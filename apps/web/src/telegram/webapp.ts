/**
 * Thin wrapper over @twa-dev/sdk (spec §4).
 *
 * Centralises ready()/expand(), initData access, theme + viewport listeners,
 * BackButton and haptics so components never touch the SDK directly. Everything
 * degrades gracefully when the app runs OUTSIDE Telegram (e.g. local dev in a
 * browser), where `WebApp` is a no-op stub.
 */
import WebApp from "@twa-dev/sdk";
import { applyTelegramTheme } from "./theme";

/** True when launched inside a real Telegram client (initData is present). */
export function isTelegramEnv(): boolean {
    return Boolean(WebApp.initData);
}

/** Raw initData query string for the Mini App auth round-trip (spec §4). */
export function getInitData(): string {
    return WebApp.initData ?? "";
}

/**
 * Boot the Mini App (spec §4): ready → true fullscreen (Bot API 8.0) with a
 * graceful fallback to expand(), map the initial theme + safe-areas, and
 * subscribe to theme / viewport / fullscreen / safe-area changes. Returns a
 * teardown that removes every listener.
 */
export function initTelegram(): () => void {
    WebApp.ready();
    requestFullscreenWithFallback();

    // Seed CSS vars from the first reports.
    applyTelegramTheme(WebApp.themeParams, WebApp.colorScheme);
    syncViewportVar();
    syncSafeAreaVars();

    const onTheme = () =>
        applyTelegramTheme(WebApp.themeParams, WebApp.colorScheme);
    const onViewport = () => syncViewportVar();
    // Fullscreen toggling and safe-area changes both move Telegram's overlaid
    // controls, so re-read the insets on each (spec §4 fullscreen handling).
    const onSafeArea = () => syncSafeAreaVars();

    WebApp.onEvent("themeChanged", onTheme);
    WebApp.onEvent("viewportChanged", onViewport);
    WebApp.onEvent("fullscreenChanged", onSafeArea);
    WebApp.onEvent("safeAreaChanged", onSafeArea);
    WebApp.onEvent("contentSafeAreaChanged", onSafeArea);

    return () => {
        WebApp.offEvent("themeChanged", onTheme);
        WebApp.offEvent("viewportChanged", onViewport);
        WebApp.offEvent("fullscreenChanged", onSafeArea);
        WebApp.offEvent("safeAreaChanged", onSafeArea);
        WebApp.offEvent("contentSafeAreaChanged", onSafeArea);
    };
}

/**
 * Request true fullscreen on Bot API 8.0+ clients; fall back to expand() on
 * desktop / old clients that reject or don't support it (spec §4). Wrapped so a
 * throwing/absent API never breaks boot.
 */
function requestFullscreenWithFallback(): void {
    try {
        if (
            typeof WebApp.isVersionAtLeast === "function" &&
            WebApp.isVersionAtLeast("8.0") &&
            typeof WebApp.requestFullscreen === "function"
        ) {
            WebApp.requestFullscreen();
            return;
        }
    } catch {
        /* fall through to expand() below */
    }
    try {
        WebApp.expand();
    } catch {
        /* no-op outside Telegram */
    }
}

/** Expose the stable viewport height so the fixed shell stays correct. */
function syncViewportVar(): void {
    const h = WebApp.viewportStableHeight || WebApp.viewportHeight;
    if (h) {
        document.documentElement.style.setProperty("--tg-viewport", `${h}px`);
    }
}

/**
 * Mirror Telegram's safe-area insets onto CSS vars (Bot API 8.0). In fullscreen
 * Telegram overlays its own close/menu controls at the top, so the fixed header
 * must clear `contentSafeAreaInset` (the area free of Telegram's own controls);
 * `safeAreaInset` covers the device notch/home-indicator. The shell combines
 * these with `env(safe-area-inset-*)` via `max()` so it works in fullscreen,
 * fullsize, and a plain browser (spec §4). No-ops to 0 outside Telegram.
 */
function syncSafeAreaVars(): void {
    const root = document.documentElement;
    const content = safeInset(WebApp.contentSafeAreaInset);
    const device = safeInset(WebApp.safeAreaInset);

    // Telegram-control clearance: the header sits below device inset + the
    // content inset (which already accounts for the overlaid Telegram chrome).
    root.style.setProperty("--tg-content-top", `${device.top + content.top}px`);
    root.style.setProperty("--tg-content-bottom", `${device.bottom + content.bottom}px`);
    root.style.setProperty("--tg-safe-top", `${device.top}px`);
    root.style.setProperty("--tg-safe-bottom", `${device.bottom}px`);
    root.style.setProperty("--tg-safe-left", `${device.left}px`);
    root.style.setProperty("--tg-safe-right", `${device.right}px`);
}

/** Defensive read of an inset object (any field may be missing/NaN). */
function safeInset(inset: {
    top?: number;
    bottom?: number;
    left?: number;
    right?: number;
} | undefined): { top: number; bottom: number; left: number; right: number } {
    const n = (v: number | undefined) => (typeof v === "number" && v > 0 ? v : 0);
    return {
        top: n(inset?.top),
        bottom: n(inset?.bottom),
        left: n(inset?.left),
        right: n(inset?.right),
    };
}

/** Light selection haptic — used on tab switch (spec §9.4). */
export function hapticSelection(): void {
    try {
        WebApp.HapticFeedback.selectionChanged();
    } catch {
        /* no-op outside Telegram */
    }
}

/** Impact haptic — used on navigate / open-sheet (spec §11.4, default light). */
export function hapticImpact(
    style: "light" | "medium" | "heavy" = "light",
): void {
    try {
        WebApp.HapticFeedback.impactOccurred(style);
    } catch {
        /* no-op outside Telegram */
    }
}

/** Notification haptic — success on save, warning on delete-confirm (§11.4). */
export function hapticNotification(
    type: "error" | "success" | "warning",
): void {
    try {
        WebApp.HapticFeedback.notificationOccurred(type);
    } catch {
        /* no-op outside Telegram */
    }
}

// NOTE: the native Telegram MainButton is intentionally NOT used for the set
// editor's SAVE. The MainButton overlays the WebApp viewport bottom and, inside
// a bottom-sheet, clipped the sheet's lowest field on real devices (GYM-53 #1 +
// GYM-54). Save now lives as a sticky in-sheet button (spec §11.4); no
// MainButton wrapper is exported here.

/** Wire Telegram's native BackButton to a handler; returns a teardown. */
export function wireBackButton(handler: () => void): () => void {
    WebApp.BackButton.onClick(handler);
    return () => {
        WebApp.BackButton.offClick(handler);
        WebApp.BackButton.hide();
    };
}

export function showBackButton(): void {
    WebApp.BackButton.show();
}

export function hideBackButton(): void {
    WebApp.BackButton.hide();
}
