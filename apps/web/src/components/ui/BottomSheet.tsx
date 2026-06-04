/**
 * The one bottom sheet (spec §11.4 / §11.5) — bottom-anchored, thumb-reachable,
 * NOT a centered modal. Generic: it holds the set editor now and is reusable.
 *
 * Owns: a grab-handle + §9.5 top hairline, a scrim over the page (tap-scrim
 * dismisses), `safe-area-inset-bottom` inset, a 240ms slide gated by
 * prefers-reduced-motion (reduced = instant), basic focus management, and the
 * BackButton ownership rule (§11.7): while the sheet is open the Telegram
 * BackButton closes the SHEET first (one back-step), not the page. Esc closes
 * too (desktop). Width never exceeds the container column.
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

            {/* Panel: bottom-anchored, container-width, safe-area inset. */}
            <div className="absolute inset-x-0 bottom-0 flex justify-center">
                <div
                    ref={panelRef}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby={titleId}
                    tabIndex={-1}
                    className="sheet-panel w-full max-w-container rounded-t-lg border-t border-hairline bg-bg px-4 pt-3 outline-none"
                    style={{
                        // Extra bottom inset keeps the last interactive field
                        // (the Reps stepper) clear of the Telegram MainButton
                        // strip that owns the viewport bottom (GYM-53 §11.7).
                        paddingBottom:
                            "calc(env(safe-area-inset-bottom) + 56px)",
                    }}
                >
                    {/* Grab handle (spec §9.5). */}
                    <div
                        aria-hidden
                        className="mx-auto mb-4 h-1 w-12 rounded-full bg-hairline"
                    />
                    {children}
                </div>
            </div>
        </div>
    );
}
