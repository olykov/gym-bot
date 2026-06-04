/**
 * The raised center action button (spec §12.1 / §12.9).
 *
 * An ACTION, not a route: a circular `--accent` (Chalk-Red, the one brand
 * accent — §9.3) button that sits in the bottom-nav's center spacer slot and is
 * lifted UPWARD above the bar's top edge so it reads as THE primary action.
 * It has no active/route state and never moves the sliding indicator.
 *
 * 56px diameter (larger than the 44px tabs), a bold `+` glyph in
 * `--button-text`, one shadow token for the lift, and a 1px `--bg` ring so the
 * circle reads as a distinct shape against the bar. Press fires a `medium`
 * impact haptic.
 *
 * The action is left PLUGGABLE: `onRecord` defaults to a no-op so the nav ships
 * independently of the record sheet. GYM-69 wires the real sheet-open by
 * passing `onRecord` down from the shell — no change to this component.
 */
import { hapticImpact } from "@/telegram/webapp";

/** Diameter of the FAB circle (px). Mirrored by FAB_LIFT consumers. */
export const FAB_SIZE = 56;
/** How far the FAB is lifted above the bar's top edge (px) — see §12.8. */
export const FAB_LIFT = 16;

interface NavFabProps {
    /**
     * The record-sheet open handler (GYM-69). Defaults to a no-op so the nav is
     * usable on its own; for now we also log a debug breadcrumb.
     */
    onRecord?: () => void;
}

export function NavFab({ onRecord }: NavFabProps) {
    const handlePress = () => {
        hapticImpact("medium");
        if (onRecord) {
            onRecord();
        } else {
            // Placeholder until GYM-69 wires the record sheet.
            console.debug("[NavFab] record action (placeholder) — wired in GYM-69");
        }
    };

    return (
        <button
            type="button"
            aria-label="Record training"
            onClick={handlePress}
            className="press-95 absolute left-1/2 z-10 flex items-center justify-center rounded-full bg-accent shadow-card"
            style={{
                width: FAB_SIZE,
                height: FAB_SIZE,
                // Centered horizontally; lifted so the circle's bottom overlaps
                // the bar and its top rises FAB_LIFT above the bar's top edge.
                top: -FAB_LIFT,
                transform: "translateX(-50%)",
                // 1px ring in --bg so the circle reads as a distinct shape.
                outline: "1px solid var(--bg)",
                outlineOffset: "1px",
            }}
        >
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                    d="M12 5v14M5 12h14"
                    stroke="var(--button-text)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                />
            </svg>
        </button>
    );
}
