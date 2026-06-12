/**
 * The one in-sheet Save button (spec §11.4 / §12.3).
 *
 * GYM-143-v2 model: SetEditor and MoveSetPanel use a content-sized
 * BottomSheet (height:auto, max-height bounded). SheetSaveButton is placed
 * in the natural flow right after the last field — the sheet hugs the content
 * so there is no dead space, and the panel's bottom edge is already positioned
 * above the BottomNav via the wrapper. No sticky, no mt-auto, no nav offset.
 *
 * In SetLogger (§12.3) the button lives in a `shrink-0` controls region at
 * the bottom of a fixedHeight flex column — the fixedHeight sheet's wrapper
 * is also above the nav, so the controls are visible. The mt-6 top margin
 * provides visual breathing room between the last stepper and SAVE in both
 * contexts.
 *
 * Shared model: one component, one style. Accent fill per §9.3, disabled when
 * the form is invalid/pending. The -mx-4/px-4 cancel the sheet body's
 * horizontal padding so the bar spans the full panel width. The --bg backdrop
 * prevents content bleeding through when the sheet scrolls.
 *
 * GYM-131 #3: the optional `success` payload swaps the content to a check
 * glyph + "Saved set n" label for the --dur-save-morph window, 1.0→1.02→1.0
 * scale on the inner span (no layout shift). `success.nonce` keys the span
 * so consecutive saves restart the animation cleanly. Reduced motion: no scale.
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
        <div
            className="-mx-4 shrink-0 bg-bg px-4 pb-1 pt-3 mt-6"
        >
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
