/**
 * The ONE empty surface (spec §10.4): Bebas headline + Sora subline + optional
 * action. Required on every data surface — new users are the most common
 * first-run and must never see a blank/broken screen (and it must not trigger
 * extra queries; ARCH §2 "empty path is the most expensive" lesson).
 */
import type { ReactNode } from "react";

interface EmptyStateProps {
    /** Optional leading glyph (an inline SVG/emoji from the caller). */
    icon?: ReactNode;
    title: string;
    subtitle?: string;
    action?: ReactNode;
}

export function EmptyState({ icon, title, subtitle, action }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center px-4 py-8 text-center">
            {icon ? <div className="mb-3 text-hint">{icon}</div> : null}
            <h2 className="font-display text-title text-text">{title}</h2>
            {subtitle ? (
                <p className="mt-2 max-w-[40ch] text-base text-hint">{subtitle}</p>
            ) : null}
            {action ? <div className="mt-4">{action}</div> : null}
        </div>
    );
}
