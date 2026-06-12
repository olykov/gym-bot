/**
 * GYM-131 #4 — a rolling digit: when `value` changes, the old number slides
 * up and out while the new one slides up and in (translateY swap, one
 * --dur-quick beat). Self-contained and reusable — inherits the surrounding
 * font (the SET heading gives it the Bebas title face).
 *
 * Mechanics: the previous value is kept as derived state (the render-phase
 * setState pattern React documents for prop-derived state); while it is
 * non-null both digits render inside the overflow-hidden `.roll-clip` and
 * the incoming digit's `animationend` clears it. Under
 * `prefers-reduced-motion` the CSS hides `.roll-out` and disables `.roll-in`
 * (instant swap) — the stale prev state is invisible and harmless.
 */
import { useState } from "react";

interface RollingNumberProps {
    /** The number to display; a change triggers one roll. */
    value: number;
}

export function RollingNumber({ value }: RollingNumberProps) {
    const [display, setDisplay] = useState(value);
    const [prev, setPrev] = useState<number | null>(null);

    if (value !== display) {
        // Derived state during render — React re-renders immediately with
        // both digits mounted, so the swap starts on the same frame.
        setPrev(display);
        setDisplay(value);
    }

    return (
        <span className="roll-clip tabular">
            {prev !== null ? (
                <span aria-hidden="true" className="roll-out">
                    {prev}
                </span>
            ) : null}
            {/* key remounts the incoming digit so a rapid double-save
                restarts the roll cleanly instead of freezing mid-animation. */}
            <span
                key={display}
                className={prev !== null ? "roll-in" : undefined}
                onAnimationEnd={() => setPrev(null)}
            >
                {display}
            </span>
        </span>
    );
}
