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
import { Outlet, useLocation } from "react-router-dom";
import { AppHeader } from "./AppHeader";
import { BottomNav } from "./BottomNav";
import { Container } from "./Container";
import { NAV_TABS } from "./navConfig";

/** Resolve the header title for the current route from the nav config. */
function titleForPath(pathname: string): string {
    const tab = NAV_TABS.find((t) => pathname.startsWith(t.to));
    return tab?.label ?? "Gym";
}

export function AppShell() {
    const location = useLocation();
    const title = titleForPath(location.pathname);

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

            <BottomNav />
        </div>
    );
}
