/**
 * Tap vs long-press disambiguation for picker tiles (GYM-82, extracted from
 * RecordPicker.tsx in GYM-127).
 *
 * Tap: fires `onTap`.
 * Long-press (~LONG_PRESS_MS): fires `onLongPress` (with a medium impact
 * haptic), suppresses `onTap`.
 * Cancels on move > MOVE_THRESHOLD_PX, on scroll (the move threshold covers
 * it), or on early pointerup. The iOS context menu is suppressed after a
 * long-press fires.
 */
import { useRef } from "react";
import { hapticImpact } from "@/telegram/webapp";

/** Long-press timer duration in ms. Midpoint of the 450–550ms range. */
const LONG_PRESS_MS = 480;

/** Max pointer movement (px) before we cancel the long-press. */
const MOVE_THRESHOLD_PX = 6;

/**
 * Hook returning props for a tile button that distinguishes tap vs long-press.
 *
 * Respects `prefers-reduced-motion` for haptic-only (no animation change
 * needed).
 */
export function useTilePressHandlers(
    onTap: () => void,
    onLongPress: () => void,
): React.HTMLAttributes<HTMLButtonElement> {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const startPosRef = useRef<{ x: number; y: number } | null>(null);
    const firedRef = useRef(false);

    function cancel(): void {
        if (timerRef.current !== null) {
            clearTimeout(timerRef.current);
            timerRef.current = null;
        }
    }

    function onPointerDown(e: React.PointerEvent<HTMLButtonElement>): void {
        // Only primary button / touch.
        if (e.button !== 0 && e.pointerType === "mouse") return;
        firedRef.current = false;
        startPosRef.current = { x: e.clientX, y: e.clientY };
        cancel();
        timerRef.current = setTimeout(() => {
            timerRef.current = null;
            firedRef.current = true;
            hapticImpact("medium");
            onLongPress();
        }, LONG_PRESS_MS);
    }

    function onPointerMove(e: React.PointerEvent<HTMLButtonElement>): void {
        if (!startPosRef.current || timerRef.current === null) return;
        const dx = Math.abs(e.clientX - startPosRef.current.x);
        const dy = Math.abs(e.clientY - startPosRef.current.y);
        if (dx > MOVE_THRESHOLD_PX || dy > MOVE_THRESHOLD_PX) {
            cancel();
        }
    }

    function onPointerUp(): void {
        if (timerRef.current !== null) {
            // Timer still running — this is a tap.
            cancel();
            if (!firedRef.current) {
                onTap();
            }
        }
        startPosRef.current = null;
    }

    function onPointerCancel(): void {
        cancel();
        startPosRef.current = null;
    }

    return {
        onPointerDown,
        onPointerMove,
        onPointerUp,
        onPointerCancel,
        // Prevent the context menu on long-press (iOS).
        onContextMenu: (e) => {
            if (firedRef.current) e.preventDefault();
        },
    };
}
