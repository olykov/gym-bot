/**
 * Per-route-entry scroll restoration for the one scrolling element — the
 * Container's <main> (GYM-116, spec §2 scroll model).
 *
 * react-router's ScrollRestoration only handles window scroll; our scroll
 * element is the container between the fixed header and bottom-nav, so the
 * shell owns the equivalent here: save scrollTop per `location.key`, restore
 * it on POP (back/forward), start at the top on PUSH/REPLACE. useLayoutEffect
 * applies the offset before paint, so there is no visible jump — and when a
 * navigation runs inside a View Transition (GYM-121), the flushSync'd render
 * commits this effect inside the transition callback, so the new snapshot is
 * captured already-scrolled.
 */
import { useLayoutEffect, type RefObject } from "react";
import { useLocation, useNavigationType } from "react-router-dom";
import { createScrollStore } from "./scrollMemory";

/** One app-wide store: every AppShell mount shares the same memory. */
const store = createScrollStore();

/**
 * Wire scroll save/restore to the scrolling element behind `ref`.
 *
 * @param ref - ref to the scroll container (the Container <main>).
 */
export function useScrollRestoration(ref: RefObject<HTMLElement>): void {
    const location = useLocation();
    const navigationType = useNavigationType();

    useLayoutEffect(() => {
        const el = ref.current;
        if (!el) return;

        // POP returns to a previously-seen entry → restore its offset.
        // PUSH/REPLACE open a new entry → start at the top.
        el.scrollTop =
            navigationType === "POP" ? store.restore(location.key) : 0;

        // Track the live offset while this entry is active. The cleanup runs
        // AFTER the next route's DOM is committed, when scrollTop may already
        // be clamped by shorter content — so save the last value observed
        // before the switch, not the post-commit read.
        let lastTop = el.scrollTop;
        const onScroll = (): void => {
            lastTop = el.scrollTop;
        };
        el.addEventListener("scroll", onScroll, { passive: true });

        return () => {
            el.removeEventListener("scroll", onScroll);
            store.save(location.key, lastTop);
        };
    }, [ref, location.key, navigationType]);
}
