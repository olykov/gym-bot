/**
 * The ONE app shell (spec §2 / §10.1) — the consistency contract.
 *
 * Fixed <AppHeader> + fixed <BottomNav> (always visible) + the single
 * <Container>. Every page renders inside this; no page builds its own chrome or
 * goes full-bleed. The faint "chalk dust" grain (spec §9.5) sits on the page
 * background behind everything (non-interactive, off under reduced motion).
 *
 * The header title comes from the active route (set per-page below), so the
 * shell stays identical while the context label changes.
 */
import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AppHeader } from "./AppHeader";
import { BottomNav } from "./BottomNav";
import { Container } from "./Container";
import { NAV_TABS } from "./navConfig";
import { formatDayHeading } from "@/components/history/historyWindow";
import { RecordSheet } from "@/components/record/RecordSheet";

/**
 * Resolve the header title for the current route. Tab routes use the nav label;
 * the History day-detail (`/history/:date`) shows the day in Bebas (§11.3) while
 * the bottom-nav stays on the History tab (a sub-route, not a separate page).
 */
function titleForPath(pathname: string): string {
    const dayMatch = pathname.match(/^\/history\/(\d{4}-\d{2}-\d{2})$/);
    if (dayMatch) return formatDayHeading(dayMatch[1]);

    const tab = NAV_TABS.find((t) => pathname.startsWith(t.to));
    return tab?.label ?? "Gym";
}

export function AppShell() {
    const location = useLocation();
    const title = titleForPath(location.pathname);

    // The record sheet lives at the shell so the center FAB (in <BottomNav>) can
    // open it from anywhere without per-page wiring (spec §12.2 / GYM-69).
    const [recordOpen, setRecordOpen] = useState(false);

    return (
        <div className="relative h-full overflow-hidden bg-secondary-bg">
            {/* Chalk-dust grain, page background only (spec §9.5). */}
            <div className="grain" />

            <AppHeader title={title} />

            {/* Only the Container scrolls (spec §2 scroll model). Re-keyed on
                route change so the page-load reveal stagger replays. */}
            <div className="relative z-10 h-full">
                <Container revealKey={location.pathname}>
                    <Outlet />
                </Container>
            </div>

            <BottomNav onRecord={() => setRecordOpen(true)} />

            {/* The record flow (spec §12) — opened by the NavFab onRecord. */}
            <RecordSheet open={recordOpen} onClose={() => setRecordOpen(false)} />
        </div>
    );
}
