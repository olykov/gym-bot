/**
 * Unit tests for the pure hold-to-repeat engine (GYM-122).
 *
 * The engine is React-free (timer-based, callback-driven) so the timing
 * contract — initial delay, base interval, acceleration, cancel, min-clamp
 * stop — is verified here with fake timers. The pointer wiring in
 * `useHoldRepeat` is a thin binding over this engine (no jsdom/RTL yet).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    HOLD_ACCELERATE_AFTER_TICKS,
    HOLD_FAST_INTERVAL_MS,
    HOLD_INITIAL_DELAY_MS,
    HOLD_INTERVAL_MS,
    createHoldRepeat,
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
