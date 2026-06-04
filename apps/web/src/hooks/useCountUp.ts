/**
 * Count-up animation for the Bebas stat numerals (spec §9.4).
 *
 * Animates 0 → target once, ~500ms ease-out, the first time a real value
 * arrives. Respects `prefers-reduced-motion` (renders the final value instantly)
 * and skips when `animate` is false (e.g. a cache hit, so cached dashboards
 * don't re-run the count). Pure rAF — no animation library (spec §1).
 */
import { useEffect, useRef, useState } from "react";

const DURATION_MS = 500;

/** Ease-out cubic, matching the reveal feel. */
function easeOut(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}

function prefersReducedMotion(): boolean {
    return (
        typeof window !== "undefined" &&
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    );
}

/**
 * @param target - the final integer value to display.
 * @param animate - run the count once (false → show the final value instantly).
 * @returns the current displayed integer.
 */
export function useCountUp(target: number, animate: boolean): number {
    const [value, setValue] = useState<number>(animate ? 0 : target);
    const started = useRef(false);

    useEffect(() => {
        if (!animate || started.current || prefersReducedMotion()) {
            setValue(target);
            return;
        }
        started.current = true;

        let raf = 0;
        const start = performance.now();
        const tick = (now: number) => {
            const t = Math.min(1, (now - start) / DURATION_MS);
            setValue(Math.round(easeOut(t) * target));
            if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [target, animate]);

    return value;
}
