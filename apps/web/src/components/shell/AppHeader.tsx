/**
 * Fixed app header (spec §10.1 / §9.5).
 *
 * Bebas-Neue title + an optional single action slot. Pinned to the top, never
 * scrolls away, respects safe-area-inset-top. A 1px hairline + a soft --bg
 * scrim let scrolled content dissolve under it (not a hard cut). The header
 * height is a token (--header-h) that the Container's top padding accounts for.
 */
import type { ReactNode } from "react";

interface AppHeaderProps {
    title: string;
    /** Optional single trailing action (a button/icon). */
    action?: ReactNode;
}

export function AppHeader({ title, action }: AppHeaderProps) {
    return (
        <header
            className="header-scrim fixed inset-x-0 top-0 z-20 border-b border-hairline"
            style={{ paddingTop: "env(safe-area-inset-top)" }}
        >
            <div className="mx-auto flex h-header max-w-container items-center justify-between px-4">
                <h1 className="font-display text-title leading-none text-text">
                    {title}
                </h1>
                {action ? <div className="flex items-center">{action}</div> : null}
            </div>
        </header>
    );
}
