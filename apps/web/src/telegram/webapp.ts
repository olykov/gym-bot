/**
 * Thin wrapper over @twa-dev/sdk (spec §4).
 *
 * Centralises ready()/expand(), initData access, theme + viewport listeners,
 * BackButton and haptics so components never touch the SDK directly. Everything
 * degrades gracefully when the app runs OUTSIDE Telegram (e.g. local dev in a
 * browser), where `WebApp` is a no-op stub.
 */
import SdkWebApp from "@twa-dev/sdk";
import { applyTelegramTheme } from "./theme";

/**
 * Resolve the live Telegram WebApp object.
 *
 * `@twa-dev/sdk` is a CJS module whose entry is `exports.default =
 * window.Telegram.WebApp`. Under Vite 8's CJS→ESM interop the default import can
 * come back as a wrapped module object whose `.ready` is missing, which crashes
 * the Mini App at boot (white screen). The SDK itself just reads
 * `window.Telegram.WebApp`, so prefer that canonical object (present in a real
 * Telegram client and identical to the SDK export), and fall back to unwrapping
 * the SDK default export if the global is absent.
 */
function resolveWebApp(): typeof SdkWebApp {
    const fromWindow =
        typeof window !== "undefined"
            ? (window as unknown as { Telegram?: { WebApp?: unknown } }).Telegram?.WebApp
            : undefined;
    if (fromWindow && typeof (fromWindow as { ready?: unknown }).ready === "function") {
        return fromWindow as typeof SdkWebApp;
    }
    let cur: unknown = SdkWebApp;
    // Unwrap nested `.default` wrappers only while one exists; stop at the first
    // object that exposes the WebApp API (or that has no further `.default`), so a
    // plain object (e.g. a unit-test mock) is never unwrapped into `undefined`.
    while (
        cur &&
        typeof (cur as { ready?: unknown }).ready !== "function" &&
        (cur as { default?: unknown }).default
    ) {
        cur = (cur as { default?: unknown }).default;
    }
    return cur as typeof SdkWebApp;
}

const WebApp = resolveWebApp();

/** True when launched inside a real Telegram client (initData is present). */
export function isTelegramEnv(): boolean {
    return Boolean(WebApp.initData);
}

/**
 * The raw Telegram language_code from the launching user, if available.
 *
 * Returns `undefined` when running outside Telegram (local dev / browser) or
 * when the WebApp user object is not present. Consumers must handle `undefined`
 * — the locale resolver maps it to the default locale. See ADR 0003 / GYM-108.
 */
export function getTelegramLanguageCode(): string | undefined {
    try {
        return WebApp.initDataUnsafe?.user?.language_code;
    } catch {
        return undefined;
    }
}

/** Raw initData query string for the Mini App auth round-trip (spec §4). */
export function getInitData(): string {
    return WebApp.initData ?? "";
}

/**
 * Subscribe to Telegram `themeChanged`; returns an unsubscribe. Routed through the
 * resolved {@link WebApp} so callers never import `@twa-dev/sdk` directly (that
 * default import is unreliable under Vite 8 — see {@link resolveWebApp}). A no-op
 * when the SDK event API is unavailable (outside Telegram).
 */
export function onThemeChanged(handler: () => void): () => void {
    if (typeof WebApp?.onEvent !== "function") return () => {};
    WebApp.onEvent("themeChanged", handler);
    return () => WebApp.offEvent?.("themeChanged", handler);
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

// ── BackButton handler stack (GYM-119) ──────────────────────────────────────
//
// The SDK fires EVERY `BackButton.onClick` subscriber on a single press, so
// nested sheets that each wired their own handler all ran at once (ManageSheet
// over the record sheet: one Back closed both). The app therefore keeps exactly
// ONE underlying SDK subscription (created lazily on first push) and dispatches
// to the TOP of this module-level stack only. Visibility is single-owner too:
// the button shows while the stack is non-empty and hides when it empties.

type BackHandler = () => void;

const backHandlers: BackHandler[] = [];
let backDispatchWired = false;

/** Fire the top-most handler only — lower layers regain Back when it pops. */
function dispatchBack(): void {
    backHandlers[backHandlers.length - 1]?.();
}

function syncBackButtonVisibility(): void {
    try {
        if (backHandlers.length > 0) WebApp.BackButton.show();
        else WebApp.BackButton.hide();
    } catch {
        /* no-op outside Telegram */
    }
}

/**
 * Push a Back handler onto the stack. While it is the top entry, a Telegram
 * Back press runs it (and ONLY it). Returns a pop function that removes the
 * entry — safe to call twice (idempotent) and safe to call out of order
 * (removes this entry wherever it sits, not blindly the top).
 *
 * @param handler - runs on Back press while top of the stack.
 * @returns pop/cleanup function (use as a React effect teardown).
 */
export function pushBackHandler(handler: BackHandler): () => void {
    if (!backDispatchWired) {
        try {
            WebApp.BackButton.onClick(dispatchBack);
            backDispatchWired = true;
        } catch {
            /* no-op outside Telegram */
        }
    }
    backHandlers.push(handler);
    syncBackButtonVisibility();
    let popped = false;
    return () => {
        if (popped) return;
        popped = true;
        const idx = backHandlers.lastIndexOf(handler);
        if (idx !== -1) backHandlers.splice(idx, 1);
        syncBackButtonVisibility();
    };
}
