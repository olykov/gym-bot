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
import { useEffect, useRef, useState } from "react";
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
     * When true the sheet is given a FIXED height (not just a max-height) so
     * the panel never jumps between content states. The height is computed to
     * sit below the fixed AppShell header and above the safe-area bottom so
     * it never overlaps either chrome bar (spec §12.2 GYM-74).
     */
    fixedHeight?: boolean;
    /**
     * Override the default Back behaviour so the caller can intercept the
     * Telegram BackButton before it closes the sheet (e.g. step nav inside
     * the picker). Return `true` to consume the event (prevent close).
     */
    onBackOverride?: () => boolean;
    /**
     * Sheet body. Scrolls internally when the sheet hits its max-height; the
     * caller may pin its own sticky footer (the SAVE) with
     * `position:sticky; bottom:0` so it stays at the panel bottom (§11.4).
     */
    children: React.ReactNode;
}

export function BottomSheet({
    open,
    onClose,
    titleId,
    fixedHeight = false,
    onBackOverride,
    children,
}: BottomSheetProps) {
    const panelRef = useRef<HTMLDivElement>(null);

    // GYM-82: track the software keyboard height via visualViewport so the
    // sheet's scroll container can pad its bottom and keep the focused add-input
    // above the keyboard. When the keyboard opens, visualViewport.height shrinks
    // relative to window.innerHeight; the difference is the keyboard height.
    // We write it as extra bottom padding on the sheet body so the input stays
    // reachable. Reset to 0 on close.
    const [keyboardPad, setKeyboardPad] = useState(0);
    useEffect(() => {
        if (!open) {
            setKeyboardPad(0);
            return;
        }
        const vv = window.visualViewport;
        if (!vv) return;
        function update(): void {
            const kbHeight = Math.max(0, window.innerHeight - (vv?.height ?? window.innerHeight));
            setKeyboardPad(kbHeight);
        }
        vv.addEventListener("resize", update);
        update();
        return () => vv.removeEventListener("resize", update);
    }, [open]);

    // BackButton ownership (§11.7): while open, Back closes the sheet first,
    // unless the caller intercepts it (e.g. for step navigation in the picker).
    useEffect(() => {
        if (!open) return;
        showBackButton();
        const handler = () => {
            if (onBackOverride) {
                const consumed = onBackOverride();
                if (consumed) return;
            }
            onClose();
        };
        const teardown = wireBackButton(handler);
        return () => {
            teardown();
            hideBackButton();
        };
    }, [open, onClose, onBackOverride]);

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
                clipped, and a caller's sticky footer stays pinned (GYM-54).
                When fixedHeight=true the height is fixed (not max) so the panel
                never jumps between content states — it sits strictly below the
                AppShell header (GYM-74). */}
            <div className="absolute inset-x-0 bottom-0 flex justify-center">
                <div
                    ref={panelRef}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby={titleId}
                    tabIndex={-1}
                    className="sheet-panel flex w-full max-w-container flex-col rounded-t-lg border-t border-hairline bg-bg pt-3 outline-none"
                    style={
                        fixedHeight
                            ? {
                                  // Fixed height: sits strictly below the AppShell header.
                                  // = viewport − (safe-area/Telegram content top) − header-h − 24px margin.
                                  // The header-h clearance ensures the picker never overlaps the fixed header.
                                  height: "calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - var(--header-h) - 24px)",
                              }
                            : {
                                  maxHeight:
                                      "calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - 24px)",
                              }
                    }
                >
                    {/* Grab handle (spec §9.5) — fixed at the top of the panel. */}
                    <div
                        aria-hidden
                        className="mx-auto mb-4 h-1 w-12 shrink-0 rounded-full bg-hairline"
                    />

                    {/* Body region: scrolls internally so the sheet NEVER clips a
                        tall editor, and a caller's sticky footer stays pinned
                        (§11.4, GYM-54). When the sheet is fixedHeight the body
                        is also flex-col so flex children (e.g. RecordPicker) can
                        fill the available space with their own overflow handling. */}
                    <div
                        className={`min-h-0 flex-1 overflow-y-auto px-4 ${fixedHeight ? "flex flex-col" : ""}`}
                        style={{
                            // GYM-82: when the keyboard is visible, add its height to the
                            // bottom padding so the focused add-input scrolls above it.
                            // The base padding accounts for safe-area + a small gap.
                            paddingBottom: keyboardPad > 0
                                ? `${keyboardPad + 12}px`
                                : "calc(max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + 12px)",
                        }}
                    >
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
