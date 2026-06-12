/**
 * The one in-sheet Save button (spec §11.4 / §12.3, GYM-143 root-cause fix).
 *
 * GYM-143: Sheets that contain a save footer (SetEditor, MoveSetPanel) now use
 * `fixedHeight=true` with a flex-column body. `SheetSaveButton` lives at the
 * END of that flex column and uses `mt-auto` so it:
 *   - For short content (fits in panel): fills the gap and anchors to the panel
 *     bottom — no dead space, no sticky needed.
 *   - For tall content (overflows panel): collapses (mt-auto = 0), renders after
 *     the last field, scrollable into view — no clipping, no overlap.
 * This replaces the previous `position:sticky; bottom:var(--nav-h)` model which
 * required a large `paddingBottom` on the scroll body and caused dead space when
 * content was short, while still leaving REPS clipped when content was tall on
 * small/keyboard-open viewports (the GYM-143 root defect).
 *
 * In `SetLogger` (§12.3) the button lives in a `shrink-0` controls region — the
 * flex column there uses a different structure (recap scrolls, controls are
 * pinned at the bottom via shrink-0). `mt-auto` is harmless there (no free
 * space in a shrink-0 region).
 *
 * Shared model: one component, one style. Accent fill per §9.3, disabled when
 * the form is invalid/pending. The -mx-4/px-4 cancel the sheet body's horizontal
 * padding so the bar spans the panel; the --bg backdrop prevents content
 * bleeding through when the sheet scrolls.
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
