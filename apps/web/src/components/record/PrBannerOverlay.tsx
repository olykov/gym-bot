/**
 * GYM-131 #5 — the in-sheet PR banner (operator experiment): on a weight-PR
 * beat, "NEW PR · {w}KG" slides down over the panel top, holds ~1.2s and
 * fades (one CSS animation, --dur-pr-banner total; useSaveChoreography's
 * timer removes the element after the same total). Chip-banner styling per
 * §9.3 — --accent-weak bg + --accent text + hairline; the accent never fills
 * a whole surface. Bebas via font-display.
 *
 * The aria-live wrapper stays mounted so screen readers announce the content
 * change politely. Reduced motion: the banner still appears (it is
 * information), instantly, and the timer still removes it — only the
 * slide/fade are off (index.css).
 */
import { useT } from "@/i18n/catalog";
import type { PrBanner } from "./useSaveChoreography";

interface PrBannerOverlayProps {
    /** The live banner model from useSaveChoreography, or null. */
    banner: PrBanner | null;
}

export function PrBannerOverlay({ banner }: PrBannerOverlayProps) {
    const { t } = useT();
    return (
        <div
            aria-live="polite"
            className="pointer-events-none absolute inset-x-0 top-0 z-10"
        >
            {banner ? (
                // key restarts the lifecycle when a second PR lands mid-banner.
                <div
                    key={banner.nonce}
                    className="pr-banner flex items-center justify-center rounded-md border border-hairline bg-accent-weak px-4 py-2"
                >
                    <span className="tabular font-display text-title leading-none text-accent">
                        {t("logger.prBanner", { weight: banner.weight })}
                    </span>
                </div>
            ) : null}
        </div>
    );
}
