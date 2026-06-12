/**
 * Directional drill-in navigation via the View Transitions API (GYM-121).
 *
 * The single integration point for route transitions: wraps `useNavigate` and,
 * when the platform supports `document.startViewTransition` AND the user does
 * not prefer reduced motion, runs the navigation inside a view transition with
 * `data-nav-transition="push|pop"` set on <html>. The CSS in index.css keys
 * the directional slide of the content area (.vt-content) off that attribute;
 * the fixed header/bottom-nav stay put (spec §2). Everything else — old
 * Telegram WebViews, reduced motion, a throwing API — falls back to the exact
 * same instant navigation the app had before.
 *
 * Scope (spec / review doc 01 §3): ONLY drill-in pairs use this hook (today
 * /history ↔ /history/:date via DayCard and the HistoryDay back handler).
 * Future detail routes opt in by calling it with a direction; tab switches
 * keep using plain NavLink/navigate and stay instant.
 */
import { useCallback } from "react";
import { flushSync } from "react-dom";
import { useNavigate, type To } from "react-router-dom";

/** Drill-in direction: forward = push (slide left), back = pop (slide right). */
export type NavDirection = "forward" | "back";

export type TransitionNavigate = (to: To | number, direction: NavDirection) => void;

interface ViewTransitionLike {
    finished?: Promise<void>;
}

type StartViewTransition = (update: () => void) => ViewTransitionLike;

/**
 * Feature-detect the View Transitions API. Pure (document + reduced-motion
 * flag injected) so the gate is unit-testable without a real WebView.
 *
 * @returns a bound `startViewTransition`, or null → navigate instantly.
 */
export function resolveViewTransition(
    doc: { startViewTransition?: unknown },
    reducedMotion: boolean,
): StartViewTransition | null {
    const start = doc.startViewTransition;
    if (typeof start !== "function" || reducedMotion) return null;
    return start.bind(doc) as StartViewTransition;
}

function prefersReducedMotion(): boolean {
    return (
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
}

/**
 * A navigate() that slides the content area in the given direction when the
 * platform allows, and degrades to an instant swap otherwise.
 */
export function useTransitionNavigate(): TransitionNavigate {
    const navigate = useNavigate();

    return useCallback(
        (to: To | number, direction: NavDirection) => {
            const go = (): void => {
                // Two branches because NavigateFunction's delta/To overloads
                // do not accept the union type.
                if (typeof to === "number") navigate(to);
                else navigate(to);
            };

            const start = resolveViewTransition(document, prefersReducedMotion());
            if (!start) {
                go();
                return;
            }

            const root = document.documentElement;
            root.dataset.navTransition = direction === "forward" ? "push" : "pop";
            const clear = (): void => {
                delete root.dataset.navTransition;
            };

            let transition: ViewTransitionLike;
            try {
                // flushSync commits the route change synchronously inside the
                // callback, so the new snapshot (including GYM-116's restored
                // scroll position, applied in a layout effect) is complete.
                transition = start(() => flushSync(go));
            } catch {
                // Bulletproof fallback (Telegram WebViews vary): if the API
                // throws before running the callback, navigate instantly.
                clear();
                go();
                return;
            }

            if (transition.finished) {
                void transition.finished.catch(() => undefined).finally(clear);
            } else {
                clear();
            }
        },
        [navigate],
    );
}
