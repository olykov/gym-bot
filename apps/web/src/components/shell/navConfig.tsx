/**
 * Bottom-nav tab config (spec §10.1 / §12.1). The four ROUTE tabs in visual
 * order: Dashboard · Progress · History · Profile. The center `+` is NOT a tab
 * here — it is an ACTION (`<NavFab>`) rendered by `<BottomNav>` between index 1
 * and 2, so it never appears in this list. Profile is now a real (stub) tab;
 * Distribution remains deferred (not added). Icons are inline token-colored
 * SVGs (no icon library — stays inside the §1 stack).
 */
import type { ReactNode } from "react";
import type { MessageKey } from "@/i18n/messages";

export interface NavTab {
    to: string;
    /** Catalog key for the tab label (GYM-109) — translated at render. */
    labelKey: MessageKey;
    icon: (active: boolean) => ReactNode;
}

const stroke = (active: boolean) => (active ? "var(--accent)" : "var(--hint)");

export const NAV_TABS: NavTab[] = [
    {
        to: "/dashboard",
        labelKey: "nav.dashboard",
        icon: (active) => (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <rect x="3" y="3" width="7" height="9" rx="1.5" stroke={stroke(active)} strokeWidth="2" />
                <rect x="14" y="3" width="7" height="5" rx="1.5" stroke={stroke(active)} strokeWidth="2" />
                <rect x="14" y="12" width="7" height="9" rx="1.5" stroke={stroke(active)} strokeWidth="2" />
                <rect x="3" y="16" width="7" height="5" rx="1.5" stroke={stroke(active)} strokeWidth="2" />
            </svg>
        ),
    },
    {
        to: "/progress",
        labelKey: "nav.progress",
        icon: (active) => (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                    d="M4 16l4-5 4 3 6-8"
                    stroke={stroke(active)}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <path d="M4 20h16" stroke={stroke(active)} strokeWidth="2" strokeLinecap="round" />
            </svg>
        ),
    },
    {
        to: "/history",
        labelKey: "nav.history",
        // A "log" mark: three short stacked horizontal bars over a baseline
        // (spec §11.1) — distinct from Dashboard's grid and Progress's line.
        icon: (active) => (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M5 6h11" stroke={stroke(active)} strokeWidth="2" strokeLinecap="round" />
                <path d="M5 11h14" stroke={stroke(active)} strokeWidth="2" strokeLinecap="round" />
                <path d="M5 16h9" stroke={stroke(active)} strokeWidth="2" strokeLinecap="round" />
                <path d="M4 20h16" stroke={stroke(active)} strokeWidth="2" strokeLinecap="round" />
            </svg>
        ),
    },
    {
        to: "/profile",
        labelKey: "nav.profile",
        // A simple person mark: a head circle over a shoulders arc — token-
        // stroked, distinct from Dashboard's grid, Progress's line, and
        // History's log (spec §12.1).
        icon: (active) => (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="12" cy="8" r="3.5" stroke={stroke(active)} strokeWidth="2" />
                <path
                    d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6"
                    stroke={stroke(active)}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </svg>
        ),
    },
    // Distribution stays deferred for a later iteration (spec §2 / §12.1).
];
