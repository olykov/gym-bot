/**
 * Horizontally-scrollable chip row (spec §10.3) — the native-feeling selector
 * shared by the muscle and exercise pickers. Each chip is a ≥44px touch target;
 * the active chip uses the `--accent-weak` pill + `--accent` text (graphical
 * accent use, a11y-OK). Selection is single-choice and drives the dependent
 * query upstream. Loading renders skeleton chips of the same height (no jump).
 */
import { Skeleton } from "@/components/ui/Skeleton";

export interface ChipOption {
    id: number;
    /** Canonical value (API name) — used as the query key upstream. */
    label: string;
    /** Optional localized display text (GYM-109); falls back to `label`. */
    display?: string;
}

interface ChipRowProps {
    label: string;
    options: ChipOption[];
    selectedId: number | null;
    onSelect: (option: ChipOption) => void;
    loading?: boolean;
}

export function ChipRow({
    label,
    options,
    selectedId,
    onSelect,
    loading = false,
}: ChipRowProps) {
    return (
        <div>
            <div className="mb-2 text-label uppercase tracking-wide text-hint">
                {label}
            </div>
            <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
                {loading
                    ? Array.from({ length: 4 }).map((_, i) => (
                          <Skeleton
                              key={i}
                              className="h-[44px] w-20 shrink-0 rounded-full"
                          />
                      ))
                    : options.map((opt) => {
                          const active = opt.id === selectedId;
                          return (
                              <button
                                  key={opt.id}
                                  type="button"
                                  onClick={() => onSelect(opt)}
                                  aria-pressed={active}
                                  className={`press-95 flex min-h-[44px] shrink-0 items-center whitespace-nowrap rounded-full px-4 text-base transition-colors ${
                                      active
                                          ? "bg-accent-weak font-semibold text-accent"
                                          : "border border-hairline text-text"
                                  }`}
                              >
                                  {opt.display ?? opt.label}
                              </button>
                          );
                      })}
            </div>
        </div>
    );
}
