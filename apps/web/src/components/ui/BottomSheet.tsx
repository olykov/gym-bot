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
 * Positioning (GYM-143-v2 root fix): ALL sheets are anchored ABOVE the
 * BottomNav. The wrapper's bottom = --nav-h + safe-area-bottom so the
 * panel's lowest pixel sits at the nav's top edge. This means no content
 * (including the SAVE / MOVE SET footer) ever falls behind the fixed nav bar.
 *
 * Two height models (GYM-143-v2):
 *
 * 1. fixedHeight=true (RecordSheet / RecordPicker — GYM-74):
 *    The panel has a FIXED height so Phase A ↔ Phase B never causes a height
 *    jump. Height fills the available vertical space from 24px below the
 *    header/top-inset down to the nav top. Body is flex-col so inner regions
 *    distribute the space (recap scrolls; controls are shrink-0 at the bottom).
 *
 * 2. Content-sized / default (SetEditor, MoveSetPanel, ManageSheet):
 *    The panel hugs its content (height: auto). Bounded by max-height = same
 *    formula as fixedHeight — panel cannot overlap the header. For short content
 *    the sheet is compact and the footer sits directly under the last field with
 *    NO dead space. For tall content the panel hits max-height; the body scrolls
 *    internally; the footer remains visible at the panel's natural bottom edge
 *    (which is already above the nav via the wrapper positioning).
 *
 * GYM-100 / keyboard: fixedHeight sheets expose keyboard height as
 * --keyboard-pad on the panel for inner slide panels (RecordPicker). Content-
 * sized sheets absorb keyboard height as paddingBottom on the body — no nav
 * clearance needed since the wrapper already clears the nav.
 */
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useT } from "@/i18n/catalog";
import { pushBackHandler } from "@/telegram/webapp";
import { useSheetDrag } from "./useSheetDrag";

/**
 * GYM-145: module-level reference counter for open sheets.
 * When the count is > 0, data-sheet-open="1" is set on <html>; CSS uses this
 * to suppress the NavFab (.fab-btn) so it does not poke through the scrim.
 * A ref-count (not boolean) handles nested sheets correctly.
 */
let sheetCount = 0;
function acquireSheetOpen(): () => void {
    if (++sheetCount === 1) {
        document.documentElement.dataset.sheetOpen = "1";
    }
    return () => {
        if (--sheetCount === 0) {
            delete document.documentElement.dataset.sheetOpen;
        }
    };
}

/**
 * Elements a Tab press may land on inside the panel (GYM-125 #4). Queried at
 * keydown time — not cached — so rows that mount/unmount while the sheet is
 * open are always covered.
 */
const FOCUSABLE_SELECTOR =
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), ' +
    '[tabindex]:not([tabindex="-1"])';

/**
 * The nav + safe-area-bottom clearance applied to the wrapper's bottom
 * (GYM-143-v2). Positions ALL sheets above the BottomNav.
 */
const NAV_CLEAR =
    "calc(var(--nav-h) + max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)))";

/**
 * Max usable sheet height: from 24px below the header/top-inset to the nav top
 * (accounting for bottom safe area). Used as `height` for fixedHeight and
 * `max-height` for content-sized sheets.
 */
const SHEET_MAX_HEIGHT =
    "calc(100dvh" +
    " - max(env(safe-area-inset-top), var(--tg-content-top, 0px))" +
    " - var(--header-h)" +
    " - var(--nav-h)" +
    " - max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))" +
    " - 24px)";

interface BottomSheetProps {
    open: boolean;
    onClose: () => void;
    /** Accessible title id wiring; rendered by the caller inside `children`. */
    titleId?: string;
    /**
     * When true the sheet is given a FIXED height (not just a max-height) so
     * the panel never jumps between content states. The height fills the
     * available vertical space between the AppShell header and the BottomNav
     * (spec §12.2 GYM-74). Use for the record sheet (Phase A ↔ Phase B).
     *
     * Default (false): the panel is CONTENT-SIZED (height: auto) bounded by
     * max-height. Short sheets (SetEditor, MoveSetPanel) hug their content;
     * no dead space; the footer sits right under the last field with no gap.
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
     * caller places its own footer after the scroll region so it is always
     * visible regardless of content height.
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

    // GYM-145: register this sheet in the global open-count so the NavFab is
    // suppressed (via data-sheet-open on <html>) whenever any sheet is open.
    // Runs once when open transitions true → false / component unmounts.
    useEffect(() => {
        if (!open) return;
        return acquireSheetOpen();
    }, [open]);

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

    // GYM-149: render through a portal to <body>, OUTSIDE the .shell-content
    // wrapper. The GYM-148 page de-emphasis puts `opacity` + `transform` on
    // .shell-content; an inline sheet (a descendant of that wrapper) would
    // inherit the opacity (going translucent → the page bleeds through it) and
    // its `position: fixed` would resolve against the transformed ancestor
    // (so it scales/drifts instead of pinning to the viewport). Portaling to
    // <body> keeps the sheet fully opaque and viewport-fixed while only the
    // page behind is scaled and dimmed. :root CSS vars still apply in <body>.
    return createPortal(
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

            {/* Wrapper: anchored ABOVE the BottomNav (GYM-143-v2 root fix).
                bottom = --nav-h + safe-area-bottom so the panel's lowest pixel
                sits at the nav's top edge. The drag gesture translates the panel
                element via panelStyle (not this wrapper) so positioning is stable
                during drags. The scrim is a sibling of this wrapper (inside the
                fixed overlay) so it covers the full viewport including the nav. */}
            <div
                className="absolute inset-x-0 flex justify-center"
                style={{ bottom: NAV_CLEAR }}
            >
                <div
                    ref={panelRef}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby={titleId}
                    tabIndex={-1}
                    className="sheet-panel flex w-full max-w-container flex-col rounded-t-lg bg-bg outline-none"
                    style={{
                        ...(fixedHeight
                            ? {
                                  // Fixed height: fills the entire space from 24px below
                                  // the header/top-inset down to the nav top.
                                  // The wrapper bottom already positions the panel above
                                  // the nav so no nav subtraction is needed here.
                                  height: SHEET_MAX_HEIGHT,
                                  // GYM-100: expose keyboard height as a CSS var so inner
                                  // slide panels (RecordPicker) can apply it as their
                                  // paddingBottom. The fixedHeight body does NOT add
                                  // keyboardPad because the RecordPicker overflow:hidden
                                  // boundary would trap the padding outside the scroll
                                  // containers, making scrollIntoView ineffective.
                                  ["--keyboard-pad" as string]: `${keyboardPad}px`,
                              }
                            : {
                                  // Content-sized: hugs content, bounded by max-height.
                                  // Short content → compact sheet, footer right after last
                                  // field, zero dead space.
                                  // Tall content → hits max-height, body scrolls, footer
                                  // visible (panel bottom is above the nav via wrapper).
                                  maxHeight: SHEET_MAX_HEIGHT,
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
                        {/* GYM-150: width via a literal value, NOT w-12. The theme
                            sets `--spacing: initial` and enumerates only
                            --spacing-0/1/2/3/4/6/8, so `w-12` never generates → the
                            handle had NO width and stretched to the full panel width,
                            painting bg-hairline as a full-width 4px STRIP across the
                            sheet header. w-[2.5rem] always generates. */}
                        <div className="mx-auto mb-4 h-1 w-[2.5rem] rounded-full bg-hairline" />
                    </div>

                    {/* Body region: scrolls internally so the sheet NEVER clips a
                        tall editor (§11.4, GYM-54). When the sheet is fixedHeight
                        the body is also flex-col so flex children (e.g. RecordPicker)
                        can fill the available space with their own overflow handling.
                        GYM-100: for fixedHeight sheets the keyboard padding is NOT
                        applied here — it is set as --keyboard-pad on the panel
                        element and consumed by inner scroll containers.
                        GYM-143-v2: for content-sized sheets the body paddingBottom
                        only clears keyboard height (no nav clearance needed — the
                        wrapper already positions the panel above the nav). */}
                    <div
                        className={`min-h-0 flex-1 overflow-y-auto px-4 ${fixedHeight ? "flex flex-col" : ""}`}
                        style={
                            fixedHeight
                                ? undefined
                                : {
                                      paddingBottom: keyboardPad > 0
                                          ? `${keyboardPad + 12}px`
                                          : "12px",
                                  }
                        }
                    >
                        {children}
                    </div>
                </div>
            </div>
        </div>,
        document.body,
    );
}
