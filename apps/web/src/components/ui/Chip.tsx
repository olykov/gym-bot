/**
 * The one display chip (spec §11.2 / §11.5, GYM-77 #2): small Sora label on an
 * --accent-weak fill with --text text. Used for muscle tags on the day card and
 * the exercise-group header. Display-only (not a filter in v1). Token-only.
 *
 * GYM-77: accepts `title` so the full name is available on hover when the chip
 * text is truncated.
 *
 * GYM-79: switched from `inline-flex … truncate` to an outer `inline-block` pill
 * wrapping a `block truncate` inner span. `text-overflow: ellipsis` does NOT apply
 * to an inline-flex box; it requires a block-level (or inline-block) container with
 * `overflow: hidden` — which the inner span provides. The outer pill stays
 * `inline-block max-w-full` so it still sizes by content and respects any width cap
 * imposed by the parent. An optional `className` prop lets callers set extra
 * constraints (e.g. max-w-[8rem]) directly on the chip instead of a wrapper span.
 */
import type { ReactNode } from "react";

export function Chip({
    children,
    title,
    className,
}: {
    children: ReactNode;
    title?: string;
    className?: string;
}) {
    return (
        <span
            className={[
                "inline-block max-w-full rounded-full bg-accent-weak px-3 py-1 text-label text-text",
                className ?? "",
            ]
                .join(" ")
                .trimEnd()}
            title={title}
        >
            {/* Inner block is what actually clips: text-overflow needs a block box. */}
            <span className="block overflow-hidden text-ellipsis whitespace-nowrap">
                {children}
            </span>
        </span>
    );
}
