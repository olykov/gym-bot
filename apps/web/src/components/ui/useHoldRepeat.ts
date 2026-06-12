/**
 * Hold-to-repeat for the Stepper's ± buttons (GYM-122, spec §11.4 nice-to-have).
 *
 * Two layers:
 *  - `createHoldRepeat` — a pure, timer-based repeat engine (no React, no DOM)
 *    so the timing contract (initial delay → interval → acceleration) is unit-
 *    testable with vitest fake timers.
 *  - `useHoldRepeat` — a thin React binding that wires the engine to pointer
 *    events: press steps once immediately, a sustained hold repeats, and
 *    pointerup / pointerleave / pointercancel cancel. The pointer is captured
 *    (same guarded idiom as SetRow) so a finger that drifts off the button
 *    keeps the hold alive on capable browsers.
 *
 * Reduced-motion: repeating is allowed (it is input, not motion) — there are
 * no animated ramp visuals to gate (spec §9.4).
 */
import { useEffect, useRef } from "react";

/** Hold must be sustained this long before repeating starts. */
export const HOLD_INITIAL_DELAY_MS = 400;
/** Base repeat interval once the hold engages. */
export const HOLD_INTERVAL_MS = 250;
/** Accelerated interval after `HOLD_ACCELERATE_AFTER_TICKS` repeats. */
export const HOLD_FAST_INTERVAL_MS = 80;
/** Repeats before the interval accelerates to the fast rate. */
export const HOLD_ACCELERATE_AFTER_TICKS = 8;

export interface HoldRepeatController {
    /** Begin a hold: first repeat after the initial delay, then the interval. */
    start: () => void;
    /** Stop repeating (idempotent; safe when never started). */
    cancel: () => void;
}

/**
 * Build a repeat engine around a tick callback.
 *
 * @param onTick - called once per repeat with a 1-based tick number. Return
 *   `false` to stop the run (e.g. the value hit its min clamp).
 * @returns start/cancel controller. `start` resets the tick count.
 */
export function createHoldRepeat(
    onTick: (tick: number) => boolean,
): HoldRepeatController {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let tick = 0;

    function cancel(): void {
        if (timer !== null) {
            clearTimeout(timer);
            timer = null;
        }
    }

    function schedule(delayMs: number): void {
        timer = setTimeout(() => {
            tick += 1;
            if (!onTick(tick)) {
                timer = null;
                return;
            }
            schedule(
                tick >= HOLD_ACCELERATE_AFTER_TICKS
                    ? HOLD_FAST_INTERVAL_MS
                    : HOLD_INTERVAL_MS,
            );
        }, delayMs);
    }

    function start(): void {
        cancel();
        tick = 0;
        schedule(HOLD_INITIAL_DELAY_MS);
    }

    return { start, cancel };
}

export interface HoldRepeatHandlers {
    onPointerDown: (e: React.PointerEvent<HTMLElement>) => void;
    onPointerUp: () => void;
    onPointerLeave: () => void;
    onPointerCancel: () => void;
    onClick: () => void;
}

/**
 * Bind hold-to-repeat to a button.
 *
 * @param onStep - performs one step. `tick` is 0 for the initial press and
 *   1-based for repeats. Return `false` when the step was clamped (nothing
 *   changed) so the repeat run stops at min.
 * @returns pointer + click handlers to spread onto the button. The initial
 *   press steps exactly once on pointerdown; the trailing synthetic click is
 *   suppressed so a tap never double-steps. Keyboard activation (Enter/Space
 *   → click with no preceding pointerdown) still steps once.
 */
export function useHoldRepeat(
    onStep: (tick: number) => boolean,
): HoldRepeatHandlers {
    // Latest callback in a ref so long-running repeat timers never read a
    // stale closure (the parent re-renders on every value change).
    const onStepRef = useRef(onStep);
    onStepRef.current = onStep;

    const engineRef = useRef<HoldRepeatController | null>(null);
    if (engineRef.current === null) {
        engineRef.current = createHoldRepeat((tick) => onStepRef.current(tick));
    }

    // True between a pointerdown (which already stepped) and its synthetic
    // click — that click must be swallowed or a tap would step twice.
    const suppressClickRef = useRef(false);

    // Unmount mid-hold (e.g. the sheet closes) must not leave a live timer.
    useEffect(() => () => engineRef.current?.cancel(), []);

    function onPointerDown(e: React.PointerEvent<HTMLElement>): void {
        // Guarded capture (SetRow idiom): older WebViews may lack it or throw.
        try {
            if (typeof e.currentTarget.setPointerCapture === "function") {
                e.currentTarget.setPointerCapture(e.pointerId);
            }
        } catch {
            /* degrade gracefully — pointerleave still cancels the hold */
        }
        suppressClickRef.current = true;
        onStepRef.current(0);
        engineRef.current?.start();
    }

    function onPointerUp(): void {
        engineRef.current?.cancel();
        // Safety net: if an odd WebView never delivers the trailing click,
        // don't leave the next keyboard activation swallowed. The click (when
        // it comes) is dispatched before this macrotask runs.
        setTimeout(() => {
            suppressClickRef.current = false;
        }, 0);
    }

    function onPointerLeave(): void {
        engineRef.current?.cancel();
    }

    function onPointerCancel(): void {
        engineRef.current?.cancel();
        suppressClickRef.current = false; // no click follows a cancel
    }

    function onClick(): void {
        if (suppressClickRef.current) {
            suppressClickRef.current = false;
            return; // pointerdown already stepped
        }
        onStepRef.current(0); // keyboard Enter/Space
    }

    return { onPointerDown, onPointerUp, onPointerLeave, onPointerCancel, onClick };
}
