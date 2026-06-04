/**
 * The one bottom sheet (spec §11.4 / §11.5) — bottom-anchored, thumb-reachable,
 * NOT a centered modal. Generic: it holds the set editor now and is reusable.
 *
 * Owns: a grab-handle + §9.5 top hairline, a scrim over the page (tap-scrim
 * dismisses), bottom safe-area inset, a 240ms slide gated by
 * prefers-reduced-motion (reduced = instant), basic focus management, and the
 * BackButton ownership rule (§11.7): while the sheet is open the Telegram
 * BackButton closes the SHEET first (one back-step), not the page. Esc closes
 * too (desktop). Width never exceeds the container column.
 *
 * Fit (GYM-54): the panel is capped at a `max-height` of roughly
 * `viewport − top-safe-inset − a margin` and is a flex column. The `children`
 * region scrolls internally (`overflow-y:auto`) so the sheet NEVER clips — a
 * tall editor scrolls inside the panel instead of running off-screen. The
 * caller's own sticky footer (the in-sheet SAVE, `position:sticky; bottom:0`)
 * therefore stays pinned to the bottom of the scroll viewport and is never
 * clipped. This replaces the native Telegram MainButton, which overlaid the
 * WebApp viewport bottom and clipped the sheet's lowest field on real devices
 * (§11.4). The body's bottom padding clears the device/Telegram bottom inset.
 */
import { useEffect, useRef } from "react";
import {
    hideBackButton,
    showBackButton,
    wireBackButton,
} from "@/telegram/webapp";

interface BottomSheetProps {
    open: boolean;
    onClose: () => void;
    /** Accessible title id wiring; rendered by the caller inside `children`. */
    titleId?: string;
    /**
     * Sheet body. Scrolls internally when the sheet hits its max-height; the
     * caller may pin its own sticky footer (the SAVE) with
     * `position:sticky; bottom:0` so it stays at the panel bottom (§11.4).
     */
    children: React.ReactNode;
}

export function BottomSheet({ open, onClose, titleId, children }: BottomSheetProps) {
    const panelRef = useRef<HTMLDivElement>(null);

    // BackButton ownership (§11.7): while open, Back closes the sheet first.
    useEffect(() => {
        if (!open) return;
        showBackButton();
        const teardown = wireBackButton(onClose);
        return () => {
            teardown();
            hideBackButton();
        };
    }, [open, onClose]);

    // Esc closes (desktop); move focus into the panel on open.
    useEffect(() => {
        if (!open) return;
        panelRef.current?.focus();
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-30">
            {/* Scrim — tap to dismiss. Darker so it reads over near-black dark. */}
            <button
                type="button"
                aria-label="Close"
                onClick={onClose}
                className="sheet-scrim absolute inset-0"
            />

            {/* Panel: bottom-anchored, container-width. A flex column capped at
                ~viewport − top-safe-inset − margin so it never grows past the
                screen; the body region scrolls internally so nothing is ever
                clipped, and a caller's sticky footer stays pinned (GYM-54). */}
            <div className="absolute inset-x-0 bottom-0 flex justify-center">
                <div
                    ref={panelRef}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby={titleId}
                    tabIndex={-1}
                    className="sheet-panel flex w-full max-w-container flex-col rounded-t-lg border-t border-hairline bg-bg pt-3 outline-none"
                    style={{
                        // Leave the top-safe inset (Telegram fullscreen controls
                        // / notch, Bot API 8.0) plus a 24px breathing margin
                        // above the sheet so a tall sheet never reaches the
                        // overlaid Telegram chrome.
                        maxHeight:
                            "calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - 24px)",
                    }}
                >
                    {/* Grab handle (spec §9.5) — fixed at the top of the panel. */}
                    <div
                        aria-hidden
                        className="mx-auto mb-4 h-1 w-12 shrink-0 rounded-full bg-hairline"
                    />

                    {/* Scrollable body. Bottom padding clears the device /
                        Telegram bottom inset so a sticky footer rests above it. */}
                    <div
                        className="min-h-0 flex-1 overflow-y-auto px-4"
                        style={{
                            paddingBottom:
                                "calc(max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + 12px)",
                        }}
                    >
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
