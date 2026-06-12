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
import { useMemo, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useT, type Translator } from "@/i18n/catalog";
import { AppHeader } from "./AppHeader";
import { BottomNav } from "./BottomNav";
import { Container } from "./Container";
import { NAV_TABS } from "./navConfig";
import { useNavigationReveal } from "./useNavigationReveal";
import { useScrollRestoration } from "./useScrollRestoration";
import { formatDayHeading } from "@/components/history/historyWindow";
import { RecordSheet } from "@/components/record/RecordSheet";
import { RecordSheetContext } from "@/components/record/RecordSheetContext";

/**
 * Resolve the header title for the current route. Tab routes use the nav label
 * (translated, GYM-109); the History day-detail (`/history/:date`) shows the
 * day in Bebas (§11.3) while the bottom-nav stays on the History tab (a
 * sub-route, not a separate page).
 */
function titleForPath(pathname: string, { t }: Translator): string {
    const dayMatch = pathname.match(/^\/history\/(\d{4}-\d{2}-\d{2})$/);
    if (dayMatch) return formatDayHeading(dayMatch[1]);

    const tab = NAV_TABS.find((nav) => pathname.startsWith(nav.to));
    return tab ? t(tab.labelKey) : t("nav.appTitle");
}

export function AppShell() {
    const location = useLocation();
    const translator = useT();
    const title = titleForPath(location.pathname, translator);

    // GYM-116: the <main> is never remounted on navigation. The reveal plays
    // on first mount / forward nav only, and the scroll offset is saved per
    // history entry + restored on back-nav (the ref points at the scrolling
    // <main> inside <Container>).
    const { reveal, replayKey } = useNavigationReveal();
    const mainRef = useRef<HTMLElement>(null);
    useScrollRestoration(mainRef);

    // The record sheet lives at the shell so the center FAB (in <BottomNav>) can
    // open it from anywhere without per-page wiring (spec §12.2 / GYM-69).
    const [recordOpen, setRecordOpen] = useState(false);

    // GYM-118: pages (empty-state CTAs) open the SAME shell-owned sheet via
    // context — no prop-drilling, no second open-state. Stable value (setState
    // identity is stable) so consumers never re-render from the provider.
    const recordSheetValue = useMemo(
        () => ({ openRecordSheet: () => setRecordOpen(true) }),
        [],
    );

    return (
        <div className="relative h-full overflow-hidden bg-secondary-bg">
            {/* Chalk-dust grain, page background only (spec §9.5). */}
            <div className="grain" />

            <AppHeader title={title} />

            {/* Only the Container scrolls (spec §2 scroll model). */}
            <div className="relative z-10 h-full">
                <Container ref={mainRef} reveal={reveal} replayKey={replayKey}>
                    <RecordSheetContext.Provider value={recordSheetValue}>
                        <Outlet />
                    </RecordSheetContext.Provider>
                </Container>
            </div>

            <BottomNav onRecord={() => setRecordOpen(true)} />

            {/* The record flow (spec §12) — opened by the NavFab onRecord. */}
            <RecordSheet open={recordOpen} onClose={() => setRecordOpen(false)} />
        </div>
    );
}
