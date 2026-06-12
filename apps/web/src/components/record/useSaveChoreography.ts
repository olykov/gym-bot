/**
 * GYM-131 — the save-choreography state machine for SetLogger (doc 03 §2).
 *
 * One hook owns every transient celebration state and its timer so a rapid
 * double-save (~1 tap/s) always interrupts cleanly: each `onSave` clears the
 * relevant pending timer and restarts the state with a fresh `nonce` (the
 * render key that remounts the animated element, restarting its CSS
 * animation). Nothing here blocks input — these are read-only render flags.
 *
 *  - `morph`  — EVERY save: the Save button shows the check + "Saved set n"
 *    content for the --dur-save-morph window, then snaps back.
 *  - `pulse` / `flareSet` — ANY PR-beat kind (GYM-133): accent pulse on the
 *    PR chip + Save button, flare on the just-saved recap row.
 *  - `banner` — WEIGHT PR only (GYM-133 calibration; operator experiment #5):
 *    the in-sheet "NEW PR · {w}KG" banner; CSS runs slide-down/hold/fade, the
 *    timer here removes the element after the same total (works under reduced
 *    motion too, where the banner shows instantly and is removed by the
 *    timer). The quiet kinds (reps-at-weight / e1rm) get pulse + flare only.
 *
 * All motion is CSS (tokens only) and gated by prefers-reduced-motion in
 * index.css; this hook only decides WHAT is on screen, never how it moves.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { PrBeatKind } from "./derive";

/** Keep in sync with --dur-save-morph (tokens.css). */
export const SAVE_MORPH_MS = 600;
/** Keep in sync with the pr-pulse/pr-flare CSS window (index.css). */
export const PR_PULSE_MS = 700;
/** Keep in sync with --dur-pr-banner (tokens.css). */
export const PR_BANNER_TOTAL_MS = 1440;

/** The Save button's transient success content (GYM-131 #3). */
export interface SaveMorph {
    set: number;
    weight: number;
    reps: number;
    /** Render key — a new save remounts the morph span (clean restart). */
    nonce: number;
}

/** The transient PR banner model (GYM-131 #5). */
export interface PrBanner {
    weight: number;
    /** Render key — a second PR mid-banner restarts the banner. */
    nonce: number;
}

interface SaveEvent {
    set: number;
    weight: number;
    reps: number;
    /**
     * GYM-133: the resolved PR-beat kind (weight > reps-at-weight > e1rm),
     * or null when nothing was beaten. "weight" = full celebration with
     * banner (the pre-GYM-133 `beatPR: true` path); the other kinds are
     * quiet (pulse + flare, no banner).
     */
    prBeat: PrBeatKind | null;
}

export interface SaveChoreography {
    pulse: boolean;
    flareSet: number | null;
    morph: SaveMorph | null;
    banner: PrBanner | null;
    /** Fire on each successful POST /training. */
    onSave: (event: SaveEvent) => void;
    /** Clear everything (exercise switch / teardown). Identity-stable. */
    reset: () => void;
}

export function useSaveChoreography(): SaveChoreography {
    const [pulse, setPulse] = useState(false);
    const [flareSet, setFlareSet] = useState<number | null>(null);
    const [morph, setMorph] = useState<SaveMorph | null>(null);
    const [banner, setBanner] = useState<PrBanner | null>(null);

    const timers = useRef<{ morph?: number; beat?: number; banner?: number }>(
        {},
    );
    const nonceRef = useRef(0);

    const clearTimers = useCallback(() => {
        const t = timers.current;
        if (t.morph !== undefined) window.clearTimeout(t.morph);
        if (t.beat !== undefined) window.clearTimeout(t.beat);
        if (t.banner !== undefined) window.clearTimeout(t.banner);
        timers.current = {};
    }, []);

    // Unmount: never leave a timer firing into a dead component.
    useEffect(() => clearTimers, [clearTimers]);

    const reset = useCallback(() => {
        clearTimers();
        setPulse(false);
        setFlareSet(null);
        setMorph(null);
        setBanner(null);
    }, [clearTimers]);

    const onSave = useCallback(({ set, weight, reps, prBeat }: SaveEvent) => {
        nonceRef.current += 1;
        const nonce = nonceRef.current;
        const t = timers.current;

        // Success morph — every save; restart cleanly on rapid double-save.
        if (t.morph !== undefined) window.clearTimeout(t.morph);
        setMorph({ set, weight, reps, nonce });
        t.morph = window.setTimeout(() => setMorph(null), SAVE_MORPH_MS);

        if (prBeat === null) return;

        // ANY PR-beat kind: chip/button pulse + row flare (GYM-104 beat,
        // extended to the quiet kinds by GYM-133)...
        if (t.beat !== undefined) window.clearTimeout(t.beat);
        setPulse(true);
        setFlareSet(set);
        t.beat = window.setTimeout(() => {
            setPulse(false);
            setFlareSet(null);
        }, PR_PULSE_MS);

        if (prBeat !== "weight") return;

        // ...plus the banner — WEIGHT PR only (GYM-133 calibration).
        if (t.banner !== undefined) window.clearTimeout(t.banner);
        setBanner({ weight, nonce });
        t.banner = window.setTimeout(() => setBanner(null), PR_BANNER_TOTAL_MS);
    }, []);

    return { pulse, flareSet, morph, banner, onSave, reset };
}
