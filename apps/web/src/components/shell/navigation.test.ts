/**
 * Unit tests for the pure navigation logic behind GYM-116 / GYM-121:
 * the per-entry scroll store and the View Transitions feature gate.
 * (DOM behavior — actual restore on POP, the slide itself — is manual smoke.)
 */
import { describe, expect, it } from "vitest";
import { createScrollStore } from "./scrollMemory";
import { resolveViewTransition } from "./useTransitionNavigate";

describe("createScrollStore (GYM-116)", () => {
    it("returns 0 for an entry that was never saved", () => {
        const store = createScrollStore();
        expect(store.restore("default")).toBe(0);
    });

    it("round-trips a saved offset per key", () => {
        const store = createScrollStore();
        store.save("abc", 420);
        store.save("def", 13);
        expect(store.restore("abc")).toBe(420);
        expect(store.restore("def")).toBe(13);
    });

    it("overwrites on re-save of the same key", () => {
        const store = createScrollStore();
        store.save("abc", 100);
        store.save("abc", 250);
        expect(store.restore("abc")).toBe(250);
    });

    it("normalises garbage offsets (NaN / negative) to 0", () => {
        const store = createScrollStore();
        store.save("nan", Number.NaN);
        store.save("neg", -50);
        expect(store.restore("nan")).toBe(0);
        expect(store.restore("neg")).toBe(0);
    });

    it("keeps stores isolated from each other", () => {
        const a = createScrollStore();
        const b = createScrollStore();
        a.save("k", 7);
        expect(b.restore("k")).toBe(0);
    });
});

describe("resolveViewTransition (GYM-121)", () => {
    it("returns null when the API is missing (old WebView)", () => {
        expect(resolveViewTransition({}, false)).toBeNull();
        expect(
            resolveViewTransition({ startViewTransition: undefined }, false),
        ).toBeNull();
    });

    it("returns null when the API exists but reduced motion is on", () => {
        const doc = { startViewTransition: () => ({}) };
        expect(resolveViewTransition(doc, true)).toBeNull();
    });

    it("returns a callable bound to the document when supported", () => {
        const calls: Array<() => void> = [];
        const doc = {
            startViewTransition(update: () => void) {
                calls.push(update);
                return { finished: Promise.resolve() };
            },
        };
        const start = resolveViewTransition(doc, false);
        expect(start).not.toBeNull();
        const update = (): void => undefined;
        const transition = start?.(update);
        expect(calls).toEqual([update]);
        expect(transition?.finished).toBeInstanceOf(Promise);
    });

    it("rejects non-function startViewTransition shapes", () => {
        expect(
            resolveViewTransition(
                { startViewTransition: "not-a-function" },
                false,
            ),
        ).toBeNull();
    });
});
