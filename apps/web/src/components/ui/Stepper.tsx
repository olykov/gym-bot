/**
 * The one numeric stepper (spec §11.4 / §11.5) — a.k.a. <NumberField>. A −
 * button, a center tappable numeric input, a + button. Reused for Weight and
 * Reps (and any future numeric field). Token-only, ≥44px targets, value in
 * Bebas/tabular-nums (no jitter on change).
 *
 * Configurable `min` / `step` / `inputMode` / `integer`. Decimal-comma is
 * normalized to a dot, so mobile keyboards that emit `,` (locale) still parse
 * (spec §11.7). The value is held as the raw string while typing so a partial
 * entry (e.g. "10.") doesn't fight the user; `onChange` reports the parsed
 * number (or `null` for empty/NaN) to the parent for Save-enable validation.
 */
import { useId } from "react";

interface StepperProps {
    label: string;
    /** Parsed value, or null when the field is empty/invalid. */
    value: number | null;
    /** Raw text the user is typing (lets "10." stay mid-entry). */
    text: string;
    onChange: (next: { text: string; value: number | null }) => void;
    min?: number;
    step?: number;
    integer?: boolean;
    inputMode?: "decimal" | "numeric";
    /** Unit suffix shown after the value (e.g. "kg"). */
    unit?: string;
}

/** Parse a user string, normalizing comma→dot; return null on empty/NaN. */
export function parseNumeric(raw: string, integer: boolean): number | null {
    const cleaned = raw.replace(",", ".").trim();
    if (cleaned === "") return null;
    const n = integer ? parseInt(cleaned, 10) : parseFloat(cleaned);
    return Number.isFinite(n) ? n : null;
}

/** Render a number back to a clean string (drops a trailing `.0`). */
function format(n: number): string {
    return String(n);
}

export function Stepper({
    label,
    value,
    text,
    onChange,
    min = 0,
    step = 1,
    integer = false,
    inputMode = "decimal",
    unit,
}: StepperProps) {
    const id = useId();

    function bump(delta: number): void {
        const base = value ?? min;
        const next = Math.max(min, base + delta);
        const rounded = integer ? Math.round(next) : Math.round(next * 100) / 100;
        onChange({ text: format(rounded), value: rounded });
    }

    function onInput(raw: string): void {
        onChange({ text: raw, value: parseNumeric(raw, integer) });
    }

    const atMin = (value ?? min) <= min;

    return (
        <div>
            <label htmlFor={id} className="text-label uppercase tracking-wide text-hint">
                {label}
            </label>
            <div className="mt-2 flex items-stretch gap-2">
                <StepButton label="decrease" disabled={atMin} onClick={() => bump(-step)}>
                    −
                </StepButton>

                <div className="flex flex-1 items-baseline justify-center gap-1 rounded-md border border-hairline bg-secondary-bg px-3">
                    <input
                        id={id}
                        type="text"
                        inputMode={inputMode}
                        value={text}
                        onChange={(e) => onInput(e.target.value)}
                        aria-label={label}
                        className="tabular w-full bg-transparent text-center font-display text-stat leading-none text-text outline-none"
                    />
                    {unit ? (
                        <span className="text-label text-hint">{unit}</span>
                    ) : null}
                </div>

                <StepButton label="increase" onClick={() => bump(step)}>
                    +
                </StepButton>
            </div>
        </div>
    );
}

function StepButton({
    children,
    onClick,
    disabled = false,
    label,
}: {
    children: React.ReactNode;
    onClick: () => void;
    disabled?: boolean;
    label: string;
}) {
    return (
        <button
            type="button"
            aria-label={label}
            disabled={disabled}
            onClick={onClick}
            className="press-95 flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-md border border-hairline bg-bg text-2xl leading-none text-text disabled:opacity-40"
        >
            {children}
        </button>
    );
}
