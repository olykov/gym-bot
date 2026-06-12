/**
 * The one bottom sheet (spec §11.4 / §11.5) — bottom-anchored, thumb-reachable,
 * NOT a centered modal. Generic: it holds the set editor now and is reusable.
 *
 * Owns: a grab-handle + §9.5 top hairline, a scrim over the page (tap-scrim
 * dismisses), bottom safe-area inset, a 240ms slide gated by
 * prefers-reduced-motion (reduced = instant), focus management (initial focus
 * into the panel + a minimal Tab/Shift+Tab focus trap that cycles within the
 * open panel — GYM-125 #4), and the BackButton ownership rule (§11.7): while
 * the sheet is open the Telegram BackButton closes the SHEET first (one
 * back-step), not the page. Back is wired through the module-level handler
 * stack (GYM-119) so nested sheets each consume one press — top sheet first.
 * Esc closes too (desktop). Width never exceeds the container column.
 * GYM-120: the grab-handle strip is a drag-to-dismiss zone (useSheetDrag) —
 * drag down past ~30% of the panel height or flick to close; otherwise it
 * springs back. The body region is NOT part of the drag zone, so internal
 * scroll is never intercepted.
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
import { useT } from "@/i18n/catalog";
import { pushBackHandler } from "@/telegram/webapp";
import { useSheetDrag } from "./useSheetDrag";

/**
 * Elements a Tab press may land on inside the panel (GYM-125 #4). Queried at
 * keydown time — not cached — so rows that mount/unmount while the sheet is
 * open are always covered.
 */
const FOCUSABLE_SELECTOR =
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), ' +
    '[tabindex]:not([tabindex="-1"])';

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
     * Stacking layer for the sheet overlay (GYM-127 z-scale tokens).
     * "sheet" (default) → var(--z-sheet); "sheet-nested" → var(--z-sheet-nested)
     * for a sheet opened on top of another sheet, so it clears the parent
     * sheet's stacking context and its scrim covers the full viewport
     * uniformly (GYM-98).
     */
    layer?: "sheet" | "sheet-nested";
    /**
     * Sheet body. Scrolls internally when the sheet hits its max-height; the
     * caller may pin its own sticky footer (the SAVE) with
     * `position:sticky; bottom:0` so it stays at the panel bottom (§11.4).
     *
     * GYM-100: In fixedHeight mode the body region itself does NOT add the
     * keyboard padding — instead the computed keyboard height is exposed as the
     * CSS variable `--keyboard-pad` on the panel element so inner scrollable
     * sub-containers (e.g. RecordPicker slide panels) can consume it directly.
     * This avoids the height escaping the RecordPicker's overflow:hidden boundary.
     */
    children: React.ReactNode;
}

export function BottomSheet({
    open,
    onClose,
    titleId,
    fixedHeight = false,
    onBackOverride,
    layer = "sheet",
    children,
}: BottomSheetProps) {
    const { t } = useT();
    const panelRef = useRef<HTMLDivElement>(null);

    // GYM-120: drag-to-dismiss. The drag zone is ONLY the grab-handle strip
    // below — never the body — so it can't fight internal scroll.
    const { handleProps, panelStyle, scrimStyle } = useSheetDrag(
        panelRef,
        onClose,
    );

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
    // GYM-119: the handler is PUSHED onto the module-level stack — a nested
    // sheet pushes on top and consumes Back alone; this sheet regains it on
    // pop. Latest callbacks live in refs so the stack entry is pushed exactly
    // once per open and never re-ordered by a callback identity change while
    // a nested sheet sits above it.
    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;
    const onBackOverrideRef = useRef(onBackOverride);
    onBackOverrideRef.current = onBackOverride;

    useEffect(() => {
        if (!open) return;
        return pushBackHandler(() => {
            const override = onBackOverrideRef.current;
            if (override && override()) return; // consumed — sheet stays open
            onCloseRef.current();
        });
    }, [open]);

    // Esc closes (desktop); initial focus into the panel + a minimal focus
    // trap (GYM-125 #4): Tab/Shift+Tab cycle within the open panel. The scrim
    // button is a sibling OUTSIDE the panel, so it is intentionally excluded
    // (the dialog is aria-modal; pointer users still tap the scrim).
    useEffect(() => {
        if (!open) return;
        panelRef.current?.focus();
        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                onClose();
                return;
            }
            if (e.key !== "Tab") return;
            const panel = panelRef.current;
            if (!panel) return;
            const focusables = Array.from(
                panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
            );
            if (focusables.length === 0) {
                e.preventDefault(); // nothing to land on — stay on the panel
                return;
            }
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            const active = document.activeElement;
            const inside =
                active instanceof HTMLElement && panel.contains(active);
            if (e.shiftKey) {
                if (!inside || active === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else if (!inside || active === last) {
                e.preventDefault();
                first.focus();
            }
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div
            className="fixed inset-0"
            style={{
                zIndex:
                    layer === "sheet-nested"
                        ? "var(--z-sheet-nested)"
                        : "var(--z-sheet)",
            }}
        >
            {/* Scrim — tap to dismiss. Darker so it reads over near-black dark. */}
            <button
                type="button"
                aria-label={t("common.close")}
                onClick={onClose}
                className="sheet-scrim absolute inset-0"
                // GYM-120: while a handle-drag is live the scrim opacity
                // follows drag progress (inline, with the entrance animation
                // pinned off so its `forwards` fill can't fight the style).
                style={scrimStyle}
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
                    className="sheet-panel flex w-full max-w-container flex-col rounded-t-lg border-t border-hairline bg-bg outline-none"
                    style={{
                        ...(fixedHeight
                            ? {
                                  // Fixed height: sits strictly below the AppShell header.
                                  // = viewport − (safe-area/Telegram content top) − header-h − 24px margin.
                                  // The header-h clearance ensures the picker never overlaps the fixed header.
                                  height: "calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - var(--header-h) - 24px)",
                                  // GYM-100: expose keyboard height as a CSS var so inner slide panels
                                  // (RecordPicker) can apply it as their paddingBottom. The body region
                                  // of a fixedHeight sheet does NOT add keyboardPad itself because the
                                  // RecordPicker's overflow:hidden boundary traps the padding outside
                                  // the panels' scroll containers, making scrollIntoView ineffective.
                                  ["--keyboard-pad" as string]: `${keyboardPad}px`,
                              }
                            : {
                                  maxHeight:
                                      "calc(100dvh - max(env(safe-area-inset-top), var(--tg-content-top, 0px)) - 24px)",
                              }),
                        // GYM-120: drag translate / snap-back transition.
                        ...panelStyle,
                    }}
                >
                    {/* Drag zone (GYM-120): the grab handle (spec §9.5) plus the
                        panel's top padding strip — and ONLY that strip, so the
                        gesture never intercepts the body's internal scroll
                        (critical for the fixedHeight record sheet). touch-none
                        keeps the browser from hijacking the vertical drag as a
                        page scroll. Decorative: scrim/Back/Esc remain the
                        accessible close paths. */}
                    <div
                        aria-hidden
                        className="shrink-0 touch-none pt-3"
                        {...handleProps}
                    >
                        <div className="mx-auto mb-4 h-1 w-12 rounded-full bg-hairline" />
                    </div>

                    {/* Body region: scrolls internally so the sheet NEVER clips a
                        tall editor, and a caller's sticky footer stays pinned
                        (§11.4, GYM-54). When the sheet is fixedHeight the body
                        is also flex-col so flex children (e.g. RecordPicker) can
                        fill the available space with their own overflow handling.
                        GYM-100: for fixedHeight sheets the keyboard padding is NOT
                        applied here — it is set as --keyboard-pad on the panel
                        element and consumed directly by inner scroll containers. */}
                    <div
                        className={`min-h-0 flex-1 overflow-y-auto px-4 ${fixedHeight ? "flex flex-col" : ""}`}
                        style={
                            fixedHeight
                                ? undefined
                                : {
                                      // Non-fixedHeight sheets: add keyboard height to paddingBottom
                                      // so the focused input scrolls above the keyboard.
                                      paddingBottom: keyboardPad > 0
                                          ? `${keyboardPad + 12}px`
                                          : "calc(max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + 12px)",
                                  }
                        }
                    >
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}
