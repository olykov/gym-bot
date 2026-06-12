/**
 * Drag-to-dismiss gesture for <BottomSheet> (GYM-120, review doc 01 §3).
 *
 * The DRAG ZONE is only the grab-handle strip at the top of the panel — never
 * the body — so the gesture can never fight the body's internal scroll
 * (critical for the fixedHeight record sheet). Pointer events with guarded
 * `setPointerCapture` (SetRow idiom); the drag translates the panel downward
 * only (transform, clamped ≥ 0) while the scrim fades with progress.
 *
 * Release past CLOSE_FRACTION of the panel height, OR a fast downward flick
 * (velocity over the last few move samples), closes the sheet; otherwise the
 * panel springs back in SNAP_BACK_MS with var(--ease-out-soft). A light
 * impact haptic fires once per gesture when the close threshold is crossed.
 *
 * Reduced-motion: the drag still follows the finger (direct manipulation is
 * allowed, spec §9.4), but snap-back and close are instant — no transition.
 *
 * Cascade note: `.sheet-scrim` / `.sheet-panel` entrance animations use
 * `forwards` fill, which beats inline `transform`/`opacity`. After the first
 * drag starts we therefore pin `animation: "none"` inline for the rest of the
 * open lifetime (the entrance has long finished by then) — re-enabling the
 * animation later would replay the slide-up.
 */
import { useEffect, useRef, useState } from "react";
import { hapticImpact } from "@/telegram/webapp";

/** Fraction of the panel height the drag must pass to dismiss on release. */
const CLOSE_FRACTION = 0.3;
/** Downward flick speed (px/ms ≈ 500px/s) that dismisses regardless of distance. */
const FLICK_VELOCITY_PX_PER_MS = 0.5;
/** A flick still needs this much travel — guards against accidental micro-flicks. */
const FLICK_MIN_DISTANCE_PX = 24;
/** Spring-back duration (matches the SetRow snap; eased by --ease-out-soft). */
const SNAP_BACK_MS = 180;
/** Velocity is measured over move samples within this trailing window. */
const VELOCITY_WINDOW_MS = 100;
/** Move samples kept for the velocity estimate. */
const MAX_SAMPLES = 8;

interface DragSample {
    t: number;
    y: number;
}

interface SheetDragHandleProps {
    onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
    onPointerMove: (e: React.PointerEvent<HTMLDivElement>) => void;
    onPointerUp: (e: React.PointerEvent<HTMLDivElement>) => void;
    onPointerCancel: (e: React.PointerEvent<HTMLDivElement>) => void;
}

interface SheetDragResult {
    /** Spread onto the drag-zone element (handle strip). */
    handleProps: SheetDragHandleProps;
    /** Merge into the panel's inline style (after the height styles). */
    panelStyle: React.CSSProperties;
    /** Merge into the scrim's inline style. */
    scrimStyle: React.CSSProperties;
}

function prefersReducedMotion(): boolean {
    return (
        typeof window !== "undefined" &&
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    );
}

/** Downward px/ms over the trailing window; ≤0 when moving up or unknown. */
function trailingVelocity(samples: DragSample[]): number {
    if (samples.length < 2) return 0;
    const newest = samples[samples.length - 1];
    let oldest = samples[0];
    for (const s of samples) {
        if (newest.t - s.t <= VELOCITY_WINDOW_MS) {
            oldest = s;
            break;
        }
    }
    const dt = newest.t - oldest.t;
    return dt > 0 ? (newest.y - oldest.y) / dt : 0;
}

/**
 * @param panelRef - the sheet panel (measured at drag start for thresholds).
 * @param onClose - called when the gesture commits to dismissal.
 */
export function useSheetDrag(
    panelRef: React.RefObject<HTMLDivElement>,
    onClose: () => void,
): SheetDragResult {
    // null = not dragging; otherwise the downward translate in px (≥ 0).
    const [dragY, setDragY] = useState<number | null>(null);
    // True for SNAP_BACK_MS after a non-dismissing release (transition window).
    const [snapping, setSnapping] = useState(false);
    // Once a drag has started, the entrance animations stay pinned off (see
    // the cascade note above) for the rest of this open lifetime.
    const [interacted, setInteracted] = useState(false);

    const startYRef = useRef(0);
    const panelHeightRef = useRef(1);
    const samplesRef = useRef<DragSample[]>([]);
    const crossedRef = useRef(false);
    const snapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;

    useEffect(
        () => () => {
            if (snapTimerRef.current !== null) clearTimeout(snapTimerRef.current);
        },
        [],
    );

    function clearSnap(): void {
        if (snapTimerRef.current !== null) {
            clearTimeout(snapTimerRef.current);
            snapTimerRef.current = null;
        }
        setSnapping(false);
    }

    function springBack(): void {
        setDragY(null);
        if (prefersReducedMotion()) return; // instant reset, no transition
        setSnapping(true);
        snapTimerRef.current = setTimeout(() => {
            snapTimerRef.current = null;
            setSnapping(false);
        }, SNAP_BACK_MS);
    }

    function onPointerDown(e: React.PointerEvent<HTMLDivElement>): void {
        clearSnap();
        startYRef.current = e.clientY;
        panelHeightRef.current = Math.max(1, panelRef.current?.offsetHeight ?? 1);
        samplesRef.current = [{ t: e.timeStamp, y: e.clientY }];
        crossedRef.current = false;
        setInteracted(true);
        setDragY(0);
        // Guarded capture (SetRow idiom): a finger that leaves the strip keeps
        // streaming move/up events here; older WebViews may lack it or throw.
        try {
            if (typeof e.currentTarget.setPointerCapture === "function") {
                e.currentTarget.setPointerCapture(e.pointerId);
            }
        } catch {
            /* degrade gracefully — the drag works while inside the strip */
        }
    }

    function onPointerMove(e: React.PointerEvent<HTMLDivElement>): void {
        if (dragY === null) return;
        const dy = Math.max(0, e.clientY - startYRef.current); // downward only
        const samples = samplesRef.current;
        samples.push({ t: e.timeStamp, y: e.clientY });
        if (samples.length > MAX_SAMPLES) samples.shift();
        if (!crossedRef.current && dy >= CLOSE_FRACTION * panelHeightRef.current) {
            crossedRef.current = true;
            hapticImpact("light"); // once per gesture, on crossing the threshold
        }
        setDragY(dy);
    }

    function onPointerUp(e: React.PointerEvent<HTMLDivElement>): void {
        if (dragY === null) return;
        const dy = Math.max(0, e.clientY - startYRef.current);
        const velocity = trailingVelocity(samplesRef.current);
        const pastDistance = dy >= CLOSE_FRACTION * panelHeightRef.current;
        const isFlick =
            velocity >= FLICK_VELOCITY_PX_PER_MS && dy >= FLICK_MIN_DISTANCE_PX;
        if (pastDistance || isFlick) {
            setDragY(null);
            onCloseRef.current(); // close is instant — the sheet unmounts
            return;
        }
        springBack();
    }

    function onPointerCancel(): void {
        if (dragY === null) return;
        springBack(); // an aborted gesture never dismisses
    }

    const dragging = dragY !== null;
    const progress = dragging
        ? Math.min(1, dragY / panelHeightRef.current)
        : 0;

    let panelStyle: React.CSSProperties = {};
    let scrimStyle: React.CSSProperties = {};
    if (interacted) {
        if (dragging) {
            panelStyle = {
                animation: "none",
                transform: `translateY(${dragY}px)`,
                transition: "none",
            };
            scrimStyle = {
                animation: "none",
                opacity: 1 - progress,
                transition: "none",
            };
        } else if (snapping) {
            const ease = `${SNAP_BACK_MS}ms var(--ease-out-soft)`;
            panelStyle = {
                animation: "none",
                transform: "translateY(0)",
                transition: `transform ${ease}`,
            };
            scrimStyle = {
                animation: "none",
                opacity: 1,
                transition: `opacity ${ease}`,
            };
        } else {
            panelStyle = { animation: "none", transform: "translateY(0)" };
            scrimStyle = { animation: "none", opacity: 1 };
        }
    }

    return {
        handleProps: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel },
        panelStyle,
        scrimStyle,
    };
}
