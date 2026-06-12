/**
 * Hold-to-repeat for the Stepper's ± buttons (GYM-122, spec §11.4 nice-to-have).
 *
 * Three layers:
 *  - `createHoldRepeat` — a pure, timer-based repeat engine (no React, no DOM)
 *    so the timing contract (initial delay → interval → acceleration) is unit-
 *    testable with vitest fake timers.
 *  - `createHoldHandlers` — a pure factory that creates the five pointer/click
 *    handler functions given a step callback and a `now` clock function. No
 *    React, no DOM — unit-testable for the GYM-138 double-step guard.
 *  - `useHoldRepeat` — a thin React binding that wires `createHoldHandlers` to
 *    stable refs so pointer events and long-running repeat timers always read
 *    the latest callback without re-creating the handlers on every render.
 *
 * Reduced-motion: repeating is allowed (it is input, not motion) — there are
 * no animated ramp visuals to gate (spec §9.4).
 *
 * GYM-138 double-step fix: the old suppressClickRef + setTimeout(0) approach
 * was racy on real Android WebViews where the setTimeout may resolve BEFORE
 * the synthetic touch→click event fires, clearing the flag too early and letting
 * the click step a second time. Replaced with a timestamp guard: store the
 * pointerdown timestamp; if a click arrives within POINTER_CLICK_GUARD_MS it
 * is the touch-generated synthetic click and is suppressed.
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

/**
 * Maximum ms between a pointerdown (which steps once) and its trailing
 * synthetic click for the click to be considered touch-generated and
 * suppressed. Real touch-tap latency is typically 0–50 ms; 300 ms is a safe
 * upper bound that does not interfere with a genuine keyboard press that
 * happens after an unrelated touch interaction (GYM-138).
 */
export const POINTER_CLICK_GUARD_MS = 300;

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
 * A minimal PointerEvent-like interface used by the pure handler factory so
 * tests can pass a stub without needing a DOM or jsdom.
 */
export interface PointerLike {
    pointerId: number;
    currentTarget: { setPointerCapture?: (id: number) => void };
}

/**
 * Pure factory: creates the five pointer/click handlers given:
 *  - `step`  — perform one step (tick 0 = initial press; 1-based for repeats).
 *  - `now`   — clock function (default `Date.now`); injectable for tests.
 *
 * No React, no DOM — call this in a test environment directly.
 * `useHoldRepeat` is a thin React wrapper over this factory.
 *
 * GYM-138: the click guard uses a timestamp instead of the old suppressClickRef
 * + setTimeout(0) approach, which was racy on real Android WebViews.
 */
export function createHoldHandlers(
    step: (tick: number) => boolean,
    now: () => number = Date.now,
): HoldRepeatHandlers {
    const engine = createHoldRepeat(step);

    // Timestamp of the most recent pointerdown (0 = no recent pointer press).
    let pointerDownTs = 0;

    function onPointerDown(e: PointerLike): void {
        // Guarded capture: older WebViews may lack setPointerCapture or throw.
        try {
            e.currentTarget.setPointerCapture?.(e.pointerId);
        } catch {
            /* degrade gracefully — pointerleave still cancels the hold */
        }
        pointerDownTs = now();
        step(0);
        engine.start();
    }

    function onPointerUp(): void {
        engine.cancel();
    }

    function onPointerLeave(): void {
        engine.cancel();
    }

    function onPointerCancel(): void {
        engine.cancel();
        // A cancel means no synthetic click will follow — reset the timestamp
        // so the next keyboard activation is never suppressed.
        pointerDownTs = 0;
    }

    function onClick(): void {
        // GYM-138: suppress the synthetic click that touch-taps emit after
        // pointerdown. POINTER_CLICK_GUARD_MS (300 ms) is safely above the
        // real pointer→click latency on touch devices (~0–50 ms) and safely
        // below the interval at which a user might tap then quickly press
        // keyboard. If pointerDownTs is 0 (reset by cancel or never set),
        // the guard is inactive and the click steps normally (keyboard).
        const elapsed = now() - pointerDownTs;
        if (pointerDownTs > 0 && elapsed < POINTER_CLICK_GUARD_MS) {
            pointerDownTs = 0; // reset for the next interaction
            return; // touch-generated synthetic click — pointerdown already stepped
        }
        step(0); // keyboard Enter/Space or genuine mouse click
    }

    return {
        onPointerDown: onPointerDown as HoldRepeatHandlers["onPointerDown"],
        onPointerUp,
        onPointerLeave,
        onPointerCancel,
        onClick,
    };
}

/**
 * React binding over `createHoldHandlers`. Stores the latest `onStep`
 * callback and the handler set in refs so pointer events and long-running
 * repeat timers always read the freshest callback without re-creating handlers
 * on every render.
 *
 * @param onStep - performs one step. `tick` is 0 for the initial press and
 *   1-based for repeats. Return `false` when the step was clamped (nothing
 *   changed) so the repeat run stops at min.
 * @returns pointer + click handlers to spread onto the button.
 */
export function useHoldRepeat(
    onStep: (tick: number) => boolean,
): HoldRepeatHandlers {
    // Latest callback in a ref so long-running repeat timers never read a
    // stale closure (the parent re-renders on every value change).
    const onStepRef = useRef(onStep);
    onStepRef.current = onStep;

    // The handler set is created once and stored in a ref. It always reads
    // the latest onStep via onStepRef.current (stable reference).
    const handlersRef = useRef<HoldRepeatHandlers | null>(null);
    if (handlersRef.current === null) {
        handlersRef.current = createHoldHandlers(
            (tick) => onStepRef.current(tick),
        );
    }

    // Cancel any in-flight hold timer on unmount (e.g. sheet closes mid-hold).
    const handlers = handlersRef.current;
    useEffect(
        () => () => {
            // Access the internal engine cancel via the onPointerCancel path —
            // this is safe because createHoldHandlers wires it to engine.cancel().
            handlers.onPointerCancel();
        },
        [handlers],
    );

    return handlers;
}
