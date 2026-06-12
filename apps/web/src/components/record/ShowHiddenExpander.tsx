/**
 * Collapsed-by-default expander for the "Show Hidden" section (GYM-103,
 * extracted from RecordPicker.tsx in GYM-127).
 *
 * Design (Chalk & Iron, tokens only):
 * - The trigger row is a text button in `--hint` with a rotated chevron arrow.
 * - Content (the hidden tile grid) renders below the trigger when open.
 * - Only rendered when `hasHidden` is true — hidden entirely when nothing is
 *   hidden (the operator's requirement: "collapsed when nothing hidden").
 * - While the hidden list is still loading, nothing is shown (avoids flash of
 *   expander→nothing when the list arrives empty).
 */
import type { ReactNode } from "react";

interface ShowHiddenExpanderProps {
    /** The full, localized trigger text (GYM-109), e.g. t("picker.showHiddenMuscles"). */
    label: string;
    isOpen: boolean;
    onToggle: () => void;
    /** True while the hidden list is loading (shows nothing while loading). */
    isLoading: boolean;
    /** True when there is at least one hidden item — controls visibility. */
    hasHidden: boolean;
    tabIndex: number;
    children: ReactNode;
}

export function ShowHiddenExpander({
    label,
    isOpen,
    onToggle,
    isLoading,
    hasHidden,
    tabIndex,
    children,
}: ShowHiddenExpanderProps) {
    if (isLoading || !hasHidden) return null;

    return (
        <div className="mt-2">
            <button
                type="button"
                tabIndex={tabIndex}
                onClick={onToggle}
                aria-expanded={isOpen}
                className="press-95 inline-flex min-h-[44px] items-center gap-2 text-label text-hint"
            >
                <span
                    aria-hidden
                    style={{
                        display: "inline-block",
                        transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
                        transition: "transform 150ms ease",
                    }}
                >
                    ›
                </span>
                {" "}{label}
            </button>
            {isOpen ? <div className="mt-2">{children}</div> : null}
        </div>
    );
}
