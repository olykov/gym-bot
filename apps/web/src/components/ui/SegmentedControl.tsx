/**
 * SegmentedControl (spec §9.3) — a token-only, two-or-more option toggle. The
 * active segment is the `--accent` voice over an `--accent-weak` track; inactive
 * segments are quiet `--hint`. Each segment is a ≥44px touch target. Used by
 * Progress to switch the chart between By Weight (trend) and By Set (GYM-57).
 *
 * Single-choice, controlled. `aria-pressed` per segment + a `group`/`label` for
 * a11y. No motion beyond a token color transition (reduced-motion safe).
 */

export interface SegmentOption<T extends string> {
    value: T;
    label: string;
}

interface SegmentedControlProps<T extends string> {
    options: SegmentOption<T>[];
    value: T;
    onChange: (value: T) => void;
    /** Accessible label for the group (visually hidden). */
    ariaLabel?: string;
}

export function SegmentedControl<T extends string>({
    options,
    value,
    onChange,
    ariaLabel,
}: SegmentedControlProps<T>) {
    return (
        <div
            role="group"
            aria-label={ariaLabel}
            className="flex gap-1 rounded-full bg-accent-weak p-1"
        >
            {options.map((opt) => {
                const active = opt.value === value;
                return (
                    <button
                        key={opt.value}
                        type="button"
                        onClick={() => onChange(opt.value)}
                        aria-pressed={active}
                        className={`press-95 flex min-h-[44px] flex-1 items-center justify-center whitespace-nowrap rounded-full px-4 text-base transition-colors ${
                            active
                                ? "bg-bg font-semibold text-accent shadow-card"
                                : "text-hint"
                        }`}
                    >
                        {opt.label}
                    </button>
                );
            })}
        </div>
    );
}
