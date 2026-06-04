/**
 * The one in-sheet sticky Save button (spec §11.4 / §12.3). Pinned to the bottom
 * of a <BottomSheet>'s scroll viewport (`position:sticky; bottom:0`) above the
 * device/Telegram bottom inset, so it never scrolls away and is never clipped —
 * this is the deliberate replacement for the native Telegram MainButton, which
 * overlaid the WebApp viewport bottom and clipped the sheet's lowest field on
 * real devices (GYM-54).
 *
 * Shared by the History set editor (§11.4) and the record-flow SetLogger (§12.3)
 * so there is exactly ONE sticky-Save style. Accent fill per §9.3, disabled when
 * the form is invalid/pending. The -mx-4/px-4 cancel the sheet body's horizontal
 * padding so the bar spans the panel; the --bg backdrop hides content scrolling
 * under it. An optional `pulse` flag fires the §9.4 single accent flare (PR-beat
 * celebration) — instant, no library, off under prefers-reduced-motion.
 */
interface SheetSaveButtonProps {
    label: string;
    onClick: () => void;
    disabled?: boolean;
    /** One accent pulse on the next render (PR-beat, §12.3). */
    pulse?: boolean;
}

export function SheetSaveButton({
    label,
    onClick,
    disabled = false,
    pulse = false,
}: SheetSaveButtonProps) {
    return (
        <div className="sticky bottom-0 z-10 -mx-4 mt-6 bg-bg px-4 pb-1 pt-3">
            <button
                type="button"
                onClick={onClick}
                disabled={disabled}
                className={`press-95 min-h-[48px] w-full rounded-md bg-accent text-base font-semibold uppercase tracking-wide text-button-text transition-opacity disabled:cursor-not-allowed disabled:opacity-40 ${
                    pulse ? "pr-pulse motion-reduce:animate-none" : ""
                }`}
            >
                {label}
            </button>
        </div>
    );
}
