/**
 * The one display chip (spec §11.2 / §11.5): small Sora label on an
 * --accent-weak fill with --text text. Used for muscle tags on the day card and
 * the exercise-group header. Display-only (not a filter in v1). Token-only.
 */
import type { ReactNode } from "react";

export function Chip({ children }: { children: ReactNode }) {
    return (
        <span className="inline-flex max-w-full items-center truncate rounded-full bg-accent-weak px-3 py-1 text-label text-text">
            {children}
        </span>
    );
}
