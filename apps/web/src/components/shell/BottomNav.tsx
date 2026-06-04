/**
 * Fixed bottom navigation (spec §10.1 / §9.4 / §12.1).
 *
 * Five slots: four route tabs (Dashboard · Progress · History · Profile) plus a
 * raised center ACTION (`<NavFab>`) rendered between visual index 1 and 2. The
 * center is a fixed-width SPACER in the flex row; the FAB is absolutely
 * positioned over it and lifts upward, so it is not a tab and never appears in
 * `NAV_TABS`.
 *
 * Always visible, never disappears. Each tab is a >=44px touch target (icon +
 * Sora label). The active tab gets the --accent glyph, an --accent-weak pill,
 * and a sliding indicator. Because the center spacer makes the slots
 * non-uniform, the indicator is positioned from the active tab's MEASURED rect
 * (ref-measured left edge + width, recomputed on resize / route change) rather
 * than the old `index * 100%` math — the center tap never moves it.
 *
 * Switching tabs fires a `selectionChanged` haptic. Clears the home-indicator /
 * Telegram bottom inset via max(env(safe-area-inset-bottom), --tg-safe-bottom)
 * (Bot API 8.0, spec §4).
 */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { hapticSelection } from "@/telegram/webapp";
import { NAV_TABS } from "./navConfig";
import { NavFab, FAB_SIZE } from "./NavFab";

/** Center spacer width — wide enough that the FAB circle + ring clears the
 *  neighbouring >=44px tabs with a >=8px gap on each side (spec §12.8). */
const CENTER_SLOT_PX = FAB_SIZE + 24; // 56 + 12px gap each side

interface BottomNavProps {
    /** Record-sheet open handler, passed straight to the FAB (GYM-69). */
    onRecord?: () => void;
}

export function BottomNav({ onRecord }: BottomNavProps) {
    const location = useLocation();
    const activeIndex = Math.max(
        0,
        NAV_TABS.findIndex((t) => location.pathname.startsWith(t.to)),
    );

    // Refs for each route tab, so the indicator can be measured (not computed
    // from a naive index, which breaks with the non-uniform center slot).
    const rowRef = useRef<HTMLDivElement>(null);
    const tabRefs = useRef<(HTMLAnchorElement | null)[]>([]);
    const [indicator, setIndicator] = useState<{ left: number; width: number }>({
        left: 0,
        width: 0,
    });

    // Measure the active tab's rect relative to the flex row and size/position
    // the indicator from it. Recompute on route change and on resize.
    useLayoutEffect(() => {
        const measure = () => {
            const row = rowRef.current;
            const tab = tabRefs.current[activeIndex];
            if (!row || !tab) return;
            const rowRect = row.getBoundingClientRect();
            const tabRect = tab.getBoundingClientRect();
            setIndicator({
                left: tabRect.left - rowRect.left,
                width: tabRect.width,
            });
        };
        measure();
        window.addEventListener("resize", measure);
        return () => window.removeEventListener("resize", measure);
    }, [activeIndex]);

    // Re-measure after fonts/layout settle on first mount.
    useEffect(() => {
        const id = requestAnimationFrame(() => {
            const row = rowRef.current;
            const tab = tabRefs.current[activeIndex];
            if (!row || !tab) return;
            const rowRect = row.getBoundingClientRect();
            const tabRect = tab.getBoundingClientRect();
            setIndicator({ left: tabRect.left - rowRect.left, width: tabRect.width });
        });
        return () => cancelAnimationFrame(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Visual order with the center spacer inserted between index 1 and 2.
    const leftTabs = NAV_TABS.slice(0, 2);
    const rightTabs = NAV_TABS.slice(2);

    const renderTab = (tab: (typeof NAV_TABS)[number], routeIndex: number) => (
        <NavLink
            key={tab.to}
            to={tab.to}
            ref={(el) => {
                tabRefs.current[routeIndex] = el;
            }}
            onClick={hapticSelection}
            className="press-95 flex min-h-[44px] flex-1 flex-col items-center justify-center gap-[2px] py-2"
        >
            {({ isActive }) => (
                <>
                    <span
                        className={
                            isActive
                                ? "rounded-md bg-accent-weak px-3 py-[2px]"
                                : "px-3 py-[2px]"
                        }
                    >
                        {tab.icon(isActive)}
                    </span>
                    <span
                        className={`text-label ${
                            isActive ? "font-semibold text-accent" : "text-hint"
                        }`}
                    >
                        {tab.label}
                    </span>
                </>
            )}
        </NavLink>
    );

    return (
        <nav
            className="fixed inset-x-0 bottom-0 z-20 border-t border-hairline bg-bg"
            style={{
                paddingBottom:
                    "max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))",
            }}
        >
            <div ref={rowRef} className="relative mx-auto flex h-nav max-w-container">
                {/* Sliding active indicator over the 4 route tabs only — sized
                    and positioned from the active tab's measured rect (§12.1). */}
                <span
                    aria-hidden
                    className="pointer-events-none absolute top-0 h-[3px] rounded-full bg-accent transition-all duration-[180ms] ease-out-soft motion-reduce:transition-none"
                    style={{
                        left: indicator.left,
                        width: indicator.width,
                    }}
                />

                {leftTabs.map((tab, i) => renderTab(tab, i))}

                {/* Fixed-width center spacer; the raised FAB sits over it. */}
                <div className="relative flex-none" style={{ width: CENTER_SLOT_PX }}>
                    <NavFab onRecord={onRecord} />
                </div>

                {rightTabs.map((tab, i) => renderTab(tab, i + leftTabs.length))}
            </div>
        </nav>
    );
}
