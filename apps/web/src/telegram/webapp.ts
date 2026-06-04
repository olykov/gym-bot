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
 * Boot the Mini App: ready + expand, map the initial theme, and subscribe to
 * theme/viewport changes. Returns a teardown that removes the listeners.
 */
export function initTelegram(): () => void {
    WebApp.ready();
    WebApp.expand();

    // Seed CSS vars from the first theme report.
    applyTelegramTheme(WebApp.themeParams, WebApp.colorScheme);
    syncViewportVar();

    const onTheme = () =>
        applyTelegramTheme(WebApp.themeParams, WebApp.colorScheme);
    const onViewport = () => syncViewportVar();

    WebApp.onEvent("themeChanged", onTheme);
    WebApp.onEvent("viewportChanged", onViewport);

    return () => {
        WebApp.offEvent("themeChanged", onTheme);
        WebApp.offEvent("viewportChanged", onViewport);
    };
}

/** Expose the stable viewport height so the fixed shell stays correct. */
function syncViewportVar(): void {
    const h = WebApp.viewportStableHeight || WebApp.viewportHeight;
    if (h) {
        document.documentElement.style.setProperty("--tg-viewport", `${h}px`);
    }
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

/**
 * Imperative MainButton control for the set-editor SAVE action (spec §11.4).
 *
 * Centralises the SDK so the sheet never touches WebApp directly and it all
 * no-ops outside Telegram. `onClick` wires a handler and returns a teardown that
 * removes it and hides the button — call it on sheet close/unmount.
 */
export const mainButton = {
    show(text: string): void {
        try {
            WebApp.MainButton.setText(text);
            WebApp.MainButton.show();
        } catch {
            /* no-op outside Telegram */
        }
    },
    hide(): void {
        try {
            WebApp.MainButton.hide();
        } catch {
            /* no-op */
        }
    },
    setEnabled(enabled: boolean): void {
        try {
            if (enabled) WebApp.MainButton.enable();
            else WebApp.MainButton.disable();
        } catch {
            /* no-op */
        }
    },
    showProgress(): void {
        try {
            WebApp.MainButton.showProgress();
        } catch {
            /* no-op */
        }
    },
    hideProgress(): void {
        try {
            WebApp.MainButton.hideProgress();
        } catch {
            /* no-op */
        }
    },
    onClick(handler: () => void): () => void {
        try {
            WebApp.MainButton.onClick(handler);
        } catch {
            /* no-op */
        }
        return () => {
            try {
                WebApp.MainButton.offClick(handler);
                WebApp.MainButton.hide();
            } catch {
                /* no-op */
            }
        };
    },
};

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
