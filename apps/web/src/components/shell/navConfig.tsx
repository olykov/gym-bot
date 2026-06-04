/**
 * Bottom-nav tab config (spec §10.1). v1 = Dashboard · Progress; Distribution
 * and Profile slots are reserved (commented) for the later iteration. Icons are
 * inline token-colored SVGs (no icon library — stays inside the §1 stack).
 */
import type { ReactNode } from "react";

export interface NavTab {
    to: string;
    label: string;
    icon: (active: boolean) => ReactNode;
}

const stroke = (active: boolean) => (active ? "var(--accent)" : "var(--hint)");

export const NAV_TABS: NavTab[] = [
    {
        to: "/dashboard",
        label: "Dashboard",
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
        label: "Progress",
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
    // Reserved for the later iteration (spec §2): Distribution · Profile.
];
