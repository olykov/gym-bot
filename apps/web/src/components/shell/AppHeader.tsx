/**
 * Fixed app header (spec §10.1 / §9.5).
 *
 * Bebas-Neue title + an optional single action slot. Pinned to the top, never
 * scrolls away, respects safe-area-inset-top. A soft --bg scrim (no hard
 * hairline) lets scrolled content dissolve under it — the scrim is the only
 * separator, so it never reads as an accidental hard cut under the blur
 * (GYM-53 #3). The header height is a token (--header-h) that the Container's
 * top padding accounts for.
 *
 * Fullscreen (Bot API 8.0): in true fullscreen Telegram overlays its own
 * close/menu controls at the very top of the WebApp, so the header must sit
 * BELOW them. We pad the top by max(env(safe-area-inset-top), --tg-content-top)
 * — the Telegram content-safe inset (set by telegram/webapp.ts) is the
 * clearance under those controls, and the env() fallback keeps the notch handled
 * in fullsize/browser (spec §4).
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
            className="header-scrim fixed inset-x-0 top-0 z-20"
            style={{
                paddingTop:
                    "max(env(safe-area-inset-top), var(--tg-content-top, 0px))",
            }}
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
