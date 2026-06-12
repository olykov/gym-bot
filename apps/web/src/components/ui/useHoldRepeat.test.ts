/**
 * Unit tests for the hold-to-repeat engine (GYM-122) and the
 * pointer→click double-step guard (GYM-138).
 *
 * `createHoldRepeat` — pure, timer-based engine; verified with fake timers.
 * `createHoldHandlers` — pure handler factory (no React, no DOM); verified
 *   for the GYM-138 double-step guard using a controllable `now` clock.
 *
 * `useHoldRepeat` is a thin React wrapper over `createHoldHandlers` and is
 * not tested here (no jsdom/RTL in the current setup).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    HOLD_ACCELERATE_AFTER_TICKS,
    HOLD_FAST_INTERVAL_MS,
    HOLD_INITIAL_DELAY_MS,
    HOLD_INTERVAL_MS,
    POINTER_CLICK_GUARD_MS,
    createHoldRepeat,
    createHoldHandlers,
} from "./useHoldRepeat";

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
});

describe("createHoldRepeat", () => {
    it("does not tick before the initial delay", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS - 1);
        expect(onTick).not.toHaveBeenCalled();
    });

    it("fires the first repeat at the initial delay with tick=1", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS);
        expect(onTick).toHaveBeenCalledTimes(1);
        expect(onTick).toHaveBeenCalledWith(1);
    });

    it("repeats at the base interval after the first tick", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS + 2 * HOLD_INTERVAL_MS);
        expect(onTick).toHaveBeenCalledTimes(3); // ticks 1, 2, 3
        expect(onTick).toHaveBeenLastCalledWith(3);
    });

    it("accelerates to the fast interval after the threshold tick", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        // Reach the acceleration threshold: tick 1 at the initial delay, then
        // (threshold − 1) more at the base interval.
        vi.advanceTimersByTime(
            HOLD_INITIAL_DELAY_MS +
                (HOLD_ACCELERATE_AFTER_TICKS - 1) * HOLD_INTERVAL_MS,
        );
        expect(onTick).toHaveBeenCalledTimes(HOLD_ACCELERATE_AFTER_TICKS);

        // The next tick must arrive at the FAST interval, not the base one.
        vi.advanceTimersByTime(HOLD_FAST_INTERVAL_MS - 1);
        expect(onTick).toHaveBeenCalledTimes(HOLD_ACCELERATE_AFTER_TICKS);
        vi.advanceTimersByTime(1);
        expect(onTick).toHaveBeenCalledTimes(HOLD_ACCELERATE_AFTER_TICKS + 1);

        // …and keeps repeating at the fast rate.
        vi.advanceTimersByTime(5 * HOLD_FAST_INTERVAL_MS);
        expect(onTick).toHaveBeenCalledTimes(HOLD_ACCELERATE_AFTER_TICKS + 6);
    });

    it("cancel stops all future ticks", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS + HOLD_INTERVAL_MS);
        expect(onTick).toHaveBeenCalledTimes(2);
        engine.cancel();
        vi.advanceTimersByTime(10_000);
        expect(onTick).toHaveBeenCalledTimes(2);
    });

    it("cancel before the initial delay means zero ticks (a quick tap)", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS - 50);
        engine.cancel();
        vi.advanceTimersByTime(10_000);
        expect(onTick).not.toHaveBeenCalled();
    });

    it("stops when onTick returns false (min-clamp interplay)", () => {
        // Simulate a − hold that hits min on the 3rd repeat: the step callback
        // reports "clamped, nothing changed" and the run must end there.
        const onTick = vi.fn((tick: number) => tick < 3);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(10_000);
        expect(onTick).toHaveBeenCalledTimes(3);
        expect(onTick).toHaveBeenLastCalledWith(3);
    });

    it("restarting resets the tick count and the acceleration ramp", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        engine.start();
        vi.advanceTimersByTime(
            HOLD_INITIAL_DELAY_MS + HOLD_ACCELERATE_AFTER_TICKS * HOLD_INTERVAL_MS,
        );
        engine.cancel();
        onTick.mockClear();

        engine.start();
        vi.advanceTimersByTime(HOLD_INITIAL_DELAY_MS);
        expect(onTick).toHaveBeenCalledTimes(1);
        expect(onTick).toHaveBeenCalledWith(1); // tick numbering restarted
        // Back to the BASE interval — the ramp did not carry over.
        vi.advanceTimersByTime(HOLD_FAST_INTERVAL_MS);
        expect(onTick).toHaveBeenCalledTimes(1);
        vi.advanceTimersByTime(HOLD_INTERVAL_MS - HOLD_FAST_INTERVAL_MS);
        expect(onTick).toHaveBeenCalledTimes(2);
    });

    it("cancel is idempotent and safe when never started", () => {
        const onTick = vi.fn().mockReturnValue(true);
        const engine = createHoldRepeat(onTick);
        expect(() => {
            engine.cancel();
            engine.cancel();
        }).not.toThrow();
    });
});

// ---------------------------------------------------------------------------
// createHoldHandlers — pointer→click double-step guard (GYM-138)
//
// Tests exercise the pure handler factory directly (no React, no DOM).
// A controllable `now` clock replaces Date.now so we can advance time
// precisely to simulate the pointer→click sequence on a real touch device.
// ---------------------------------------------------------------------------

/** Minimal PointerLike stub — only the fields createHoldHandlers needs. */
function makePointerStub(): Parameters<ReturnType<typeof createHoldHandlers>["onPointerDown"]>[0] {
    return {
        pointerId: 1,
        currentTarget: { setPointerCapture: vi.fn() },
    } as unknown as Parameters<ReturnType<typeof createHoldHandlers>["onPointerDown"]>[0];
}

describe("createHoldHandlers — GYM-138 double-step guard", () => {
    it("pointerdown → pointerup → click: steps exactly ONCE (not twice)", () => {
        let fakeNow = 1_000_000;
        const now = () => fakeNow;
        const onStep = vi.fn().mockReturnValue(true);
        const h = createHoldHandlers(onStep, now);

        // Touch tap sequence: down (steps once) → up → synthetic click.
        h.onPointerDown(makePointerStub());
        expect(onStep).toHaveBeenCalledTimes(1);

        h.onPointerUp();

        // Synthetic click arrives 10 ms after pointerdown — within the guard.
        fakeNow += 10;
        h.onClick();
        // Must still be exactly 1 — the click was suppressed.
        expect(onStep).toHaveBeenCalledTimes(1);
    });

    it("pointerdown → pointerup → late click (>guard window): steps twice", () => {
        // A click arriving AFTER the guard window is a new genuine activation.
        let fakeNow = 1_000_000;
        const now = () => fakeNow;
        const onStep = vi.fn().mockReturnValue(true);
        const h = createHoldHandlers(onStep, now);

        h.onPointerDown(makePointerStub());
        expect(onStep).toHaveBeenCalledTimes(1);

        h.onPointerUp();

        // Click arrives well after the guard window.
        fakeNow += POINTER_CLICK_GUARD_MS + 1;
        h.onClick();
        expect(onStep).toHaveBeenCalledTimes(2);
    });

    it("no prior pointerdown → standalone click steps once (keyboard activation)", () => {
        const now = () => 1_000_000;
        const onStep = vi.fn().mockReturnValue(true);
        const h = createHoldHandlers(onStep, now);

        // No pointerdown — click from keyboard Enter/Space.
        h.onClick();
        expect(onStep).toHaveBeenCalledTimes(1);
        expect(onStep).toHaveBeenCalledWith(0);
    });

    it("pointercancel clears the guard so a subsequent click is not suppressed", () => {
        let fakeNow = 1_000_000;
        const now = () => fakeNow;
        const onStep = vi.fn().mockReturnValue(true);
        const h = createHoldHandlers(onStep, now);

        h.onPointerDown(makePointerStub()); // steps once
        h.onPointerCancel();               // cancel clears timestamp to 0

        // Click immediately after cancel — timestamp is 0 so guard is inactive.
        fakeNow += 5;
        h.onClick();
        expect(onStep).toHaveBeenCalledTimes(2); // pointerdown + click
    });

    it("second tap after the guard expires steps once per tap (no state leak)", () => {
        let fakeNow = 1_000_000;
        const now = () => fakeNow;
        const onStep = vi.fn().mockReturnValue(true);
        const h = createHoldHandlers(onStep, now);

        // First tap.
        h.onPointerDown(makePointerStub());
        h.onPointerUp();
        fakeNow += 10;
        h.onClick(); // suppressed — total: 1
        expect(onStep).toHaveBeenCalledTimes(1);

        // Guard was reset by the suppressed click. Second tap after a long pause.
        fakeNow += POINTER_CLICK_GUARD_MS + 500;
        h.onPointerDown(makePointerStub()); // steps again — total: 2
        h.onPointerUp();
        fakeNow += 10;
        h.onClick(); // suppressed — total still: 2
        expect(onStep).toHaveBeenCalledTimes(2);
    });
});
