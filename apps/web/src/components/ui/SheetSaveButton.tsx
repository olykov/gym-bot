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
 *
 * GYM-131 #3: the optional `success` payload swaps the content to a check
 * glyph (inline SVG, not emoji) + the caller's "Saved set n" label for the
 * --dur-save-morph window, with a 1.0→1.02→1.0 scale on the inner span only
 * (no layout shift — the button height is fixed). The button stays fully
 * interactive during the morph; `success.nonce` keys the span so a rapid
 * double-save remounts it and restarts the animation cleanly. Reduced
 * motion: no scale (content still swaps — it is feedback, not motion).
 */

/** Transient success content (GYM-131) — see useSaveChoreography. */
export interface SaveSuccessContent {
    /** Pre-translated "Saved set {n} — {w}×{r}" label. */
    label: string;
    /** Remount key so consecutive saves restart the morph animation. */
    nonce: number;
}

interface SheetSaveButtonProps {
    label: string;
    onClick: () => void;
    disabled?: boolean;
    /** One accent pulse on the next render (PR-beat, §12.3). */
    pulse?: boolean;
    /** GYM-131: success morph content, or null/omitted for the plain label. */
    success?: SaveSuccessContent | null;
}

export function SheetSaveButton({
    label,
    onClick,
    disabled = false,
    pulse = false,
    success = null,
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
                {success ? (
                    <span
                        key={success.nonce}
                        className="save-morph inline-flex items-center justify-center gap-2"
                    >
                        <svg
                            aria-hidden="true"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="h-4 w-4 shrink-0"
                        >
                            <path d="M2.5 8.5 6 12l7.5-7.5" />
                        </svg>
                        {success.label}
                    </span>
                ) : (
                    label
                )}
            </button>
        </div>
    );
}
