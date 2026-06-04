/**
 * Fixed bottom navigation (spec §10.1 / §9.4).
 *
 * Always visible, never disappears — replaces the old burger menu. Each tab is
 * a >=44px touch target (icon + Sora label). The active tab gets the --accent
 * glyph and a sliding indicator that translates under the active tab (180ms,
 * gated by prefers-reduced-motion). Switching tabs fires a Telegram
 * `selectionChanged` haptic. Clears the home-indicator / Telegram bottom inset
 * via max(env(safe-area-inset-bottom), --tg-safe-bottom) (Bot API 8.0, spec §4).
 */
import { NavLink, useLocation } from "react-router-dom";
import { hapticSelection } from "@/telegram/webapp";
import { NAV_TABS } from "./navConfig";

export function BottomNav() {
    const location = useLocation();
    const activeIndex = Math.max(
        0,
        NAV_TABS.findIndex((t) => location.pathname.startsWith(t.to)),
    );
    const tabCount = NAV_TABS.length;

    return (
        <nav
            className="fixed inset-x-0 bottom-0 z-20 border-t border-hairline bg-bg"
            style={{
                paddingBottom:
                    "max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))",
            }}
        >
            <div className="relative mx-auto flex h-nav max-w-container">
                {/* Sliding active indicator (spec §9.4). */}
                <span
                    aria-hidden
                    className="pointer-events-none absolute top-0 h-[3px] rounded-full bg-accent transition-transform duration-[180ms] ease-out-soft motion-reduce:transition-none"
                    style={{
                        width: `${100 / tabCount}%`,
                        transform: `translateX(${activeIndex * 100}%)`,
                    }}
                />
                {NAV_TABS.map((tab) => (
                    <NavLink
                        key={tab.to}
                        to={tab.to}
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
                ))}
            </div>
        </nav>
    );
}
