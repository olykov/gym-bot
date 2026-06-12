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
 *
 * GYM-122: holding ± repeats the step (400ms delay → 250ms, accelerating to
 * 80ms after ~8 repeats) via useHoldRepeat. A quick press still steps exactly
 * once; repeats stop at the min clamp. Light impact haptic on the first
 * repeat, then every 5th — never on the initial press (unchanged tap feel).
 */
import { useId } from "react";
import { useT } from "@/i18n/catalog";
import { hapticImpact } from "@/telegram/webapp";
import { useHoldRepeat } from "./useHoldRepeat";

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
// Exported next to the component because it IS the Stepper's input contract
// (SetLogger parses with the exact same rules the field types with); editing
// this file falls back to a full reload instead of fast refresh — acceptable.
// eslint-disable-next-line react-refresh/only-export-components
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
    const { t } = useT();
    const id = useId();

    /** Step once by delta; false when clamped at min (nothing changed). */
    function stepBy(delta: number): boolean {
        const base = value ?? min;
        const next = Math.max(min, base + delta);
        if (next === base) return false; // at the min clamp — repeats stop here
        const rounded = integer ? Math.round(next) : Math.round(next * 100) / 100;
        onChange({ text: format(rounded), value: rounded });
        return true;
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
                <StepButton
                    label={t("stepper.decrease")}
                    disabled={atMin}
                    onStep={() => stepBy(-step)}
                >
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

                <StepButton label={t("stepper.increase")} onStep={() => stepBy(step)}>
                    +
                </StepButton>
            </div>
        </div>
    );
}

function StepButton({
    children,
    onStep,
    disabled = false,
    label,
}: {
    children: React.ReactNode;
    /** Step once; return false when clamped (stops a hold's repeats). */
    onStep: () => boolean;
    disabled?: boolean;
    label: string;
}) {
    // GYM-122: tick 0 is the initial press (no haptic — unchanged tap feel);
    // repeats get a light impact on the first tick, then every 5th, and only
    // when a step actually happened (never at the min clamp).
    const hold = useHoldRepeat((tick) => {
        const stepped = onStep();
        if (stepped && tick > 0 && (tick === 1 || tick % 5 === 0)) {
            hapticImpact("light");
        }
        return stepped;
    });
    return (
        <button
            type="button"
            aria-label={label}
            disabled={disabled}
            onPointerDown={hold.onPointerDown}
            onPointerUp={hold.onPointerUp}
            onPointerLeave={hold.onPointerLeave}
            onPointerCancel={hold.onPointerCancel}
            onClick={hold.onClick}
            // touch-none: a hold must repeat, not turn into a sheet scroll.
            className="press-95 flex h-[52px] w-[52px] shrink-0 touch-none items-center justify-center rounded-md border border-hairline bg-bg text-2xl leading-none text-text disabled:opacity-40"
        >
            {children}
        </button>
    );
}
