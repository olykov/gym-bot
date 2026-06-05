/**
 * The one display chip (spec §11.2 / §11.5, GYM-77 #2): small Sora label on an
 * --accent-weak fill with --text text. Used for muscle tags on the day card and
 * the exercise-group header. Display-only (not a filter in v1). Token-only.
 *
 * GYM-77: accepts `title` so the full name is available on hover when the chip
 * text is truncated (the chip already has truncate + max-w-full for the clip).
 */
import type { ReactNode } from "react";

export function Chip({ children, title }: { children: ReactNode; title?: string }) {
    return (
        <span
            className="inline-flex max-w-full items-center truncate rounded-full bg-accent-weak px-3 py-1 text-label text-text"
            title={title}
        >
            {children}
        </span>
    );
}
