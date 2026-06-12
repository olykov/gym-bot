/**
 * In-sheet inline add field (spec §12.2, GYM-77 #2) — a tiny text input +
 * a confirm action for the `+ Muscle` / `+ Exercise` add-inline flow and the
 * new-user "ADD YOUR FIRST EXERCISE" prompt. No new screen, no modal: it lives
 * inside the record sheet body. Token-only, ≥44px targets.
 *
 * GYM-77: accepts `maxLength` (from MUSCLE_NAME_MAX / EXERCISE_NAME_MAX in
 * validation.ts) to enforce the API limits at the input level. The server is
 * still authoritative — a 422 from the API surfaces as the `error` prop message.
 *
 * On submit it reports the trimmed name to the parent (which fires the create
 * mutation + optimistic insert). It stays controlled by the parent for `pending`
 * and `error` so a failed create keeps the typed name (spec §12.5). Submit is
 * disabled while empty after trim or pending.
 *
 * GYM-82: accepts `initialValue` to pre-fill the field for rename flows.
 *
 * GYM-100: the keyboard-inset handling has moved to the slide panels
 * (RecordPicker) via the --keyboard-pad CSS variable set by BottomSheet.
 * scrollIntoView on focus was removed — it conflicted with the CSS-var approach
 * and caused jank by running before visualViewport fired its resize event.
 */
import { useState } from "react";
import { useT } from "@/i18n/catalog";

interface AddInlineFieldProps {
    placeholder: string;
    /** Label for the submit button (e.g. "Add"). */
    actionLabel: string;
    /**
     * Maximum character count for the input (GYM-77 #2 — mirrors API limits).
     * Use MUSCLE_NAME_MAX or EXERCISE_NAME_MAX from src/validation.ts.
     */
    maxLength?: number;
    /**
     * Pre-fill the field with this value (GYM-82 rename flow). The user can
     * edit; the initial trimmed value is shown and selected on focus.
     */
    initialValue?: string;
    pending?: boolean;
    error?: string | null;
    onSubmit: (name: string) => void;
    onCancel?: () => void;
}

export function AddInlineField({
    placeholder,
    actionLabel,
    maxLength,
    initialValue = "",
    pending = false,
    error = null,
    onSubmit,
    onCancel,
}: AddInlineFieldProps) {
    const { t } = useT();
    const [name, setName] = useState(initialValue);
    const trimmed = name.trim();
    const canSubmit = trimmed.length > 0 && !pending;

    function submit(): void {
        if (!canSubmit) return;
        onSubmit(trimmed);
    }

    return (
        <div>
            <div className="flex items-stretch gap-2">
                <input
                    type="text"
                    value={name}
                    autoFocus
                    placeholder={placeholder}
                    maxLength={maxLength}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            submit();
                        }
                    }}
                    className="min-h-[44px] flex-1 rounded-md border border-hairline bg-secondary-bg px-3 text-base text-text outline-none placeholder:text-hint"
                />
                <button
                    type="button"
                    onClick={submit}
                    disabled={!canSubmit}
                    className="press-95 min-h-[44px] shrink-0 rounded-md bg-accent px-4 text-base font-semibold uppercase tracking-wide text-button-text disabled:opacity-40"
                >
                    {pending ? "…" : actionLabel}
                </button>
                {onCancel ? (
                    <button
                        type="button"
                        onClick={onCancel}
                        aria-label={t("common.cancel")}
                        className="press-95 min-h-[44px] shrink-0 rounded-md border border-hairline bg-bg px-3 text-base text-hint"
                    >
                        ×
                    </button>
                ) : null}
            </div>
            {error ? (
                <p className="mt-2 text-label text-accent">{error}</p>
            ) : null}
        </div>
    );
}
