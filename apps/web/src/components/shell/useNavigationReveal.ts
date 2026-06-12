/**
 * Decide when the §9.4 reveal stagger plays (GYM-116).
 *
 * Spec: the entrance plays on first mount and on forward (PUSH/REPLACE)
 * navigations — never on POP (back), where the user returns to content they
 * have already seen and just wants their place back.
 *
 * Two outputs:
 * - `reveal`   — whether the Container should apply the .reveal-stagger class
 *   for the current entry (the class drives the CSS-only :nth-child stagger).
 * - `replayKey` — advances ONLY when the reveal plays. Keying the stagger
 *   wrapper with it remounts the children on forward nav (fresh DOM nodes =
 *   the CSS animation replays even when the route component type is reused,
 *   e.g. day → day), while POP keeps the key stable.
 *
 * The decision is computed once per `location.key` via guarded render-phase
 * refs (the React "derive from previous render" pattern) — no effects, so the
 * first paint of a new route already has the right class.
 */
import { useRef } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

export interface NavigationReveal {
    /** Apply the reveal stagger for the current history entry. */
    reveal: boolean;
    /** Sticky key for the stagger wrapper — changes on forward nav only. */
    replayKey: string;
}

export function useNavigationReveal(): NavigationReveal {
    const location = useLocation();
    // NOTE: the router reports POP for the very first entry too — the
    // `seenKey === null` check below keeps the initial mount (deep links
    // included) revealing as the spec demands.
    const navigationType = useNavigationType();

    const seenKey = useRef<string | null>(null);
    const reveal = useRef(true);
    const replayKey = useRef(location.key);

    if (seenKey.current !== location.key) {
        reveal.current = seenKey.current === null || navigationType !== "POP";
        if (reveal.current) replayKey.current = location.key;
        seenKey.current = location.key;
    }

    return { reveal: reveal.current, replayKey: replayKey.current };
}
