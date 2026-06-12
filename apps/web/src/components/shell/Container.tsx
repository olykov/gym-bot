/**
 * The single content container (spec §2 / §10.1). The ONLY place page content
 * mounts: one max-width (~480px), one horizontal padding (16px), one vertical
 * rhythm. It owns the scroll model — only this area scrolls, with top/bottom
 * padding clearing the fixed header and bottom-nav. The clearance uses
 * max(env(safe-area-inset-*), var(--tg-*)) so it accounts for Telegram's
 * fullscreen content-safe inset (Bot API 8.0) AND the device notch/home
 * indicator in fullsize/browser (spec §4). The bottom clearance also adds the
 * center FAB's lift (--fab-lift) on top of the nav height so nothing
 * interactive at the content bottom hides under the raised circle (spec §12.8).
 *
 * GYM-116: the <main> is NEVER re-keyed — it is the scroll container, and
 * remounting it on navigation wiped the scroll position. The §9.4 reveal
 * stagger is CSS-only now (.reveal-stagger > :nth-child delays in index.css)
 * and lives on the inner wrapper: `reveal` toggles the class (off on back-nav)
 * and `replayKey` re-keys ONLY the wrapper so forward navigation gets fresh
 * children (= the entrance replays). The forwarded ref exposes the scrolling
 * element to the shell's useScrollRestoration.
 *
 * GYM-121: `vt-content` names this <main> as the view-transition target, so
 * drill-in route transitions slide just the content area while the fixed
 * header/bottom-nav hold still (spec §2).
 */
import { forwardRef, type ReactNode } from "react";

interface ContainerProps {
    children: ReactNode;
    /** Play the §9.4 reveal stagger for this entry (first mount / PUSH only). */
    reveal?: boolean;
    /** Changes on forward navigation only — remounts the stagger wrapper. */
    replayKey?: string;
}

export const Container = forwardRef<HTMLElement, ContainerProps>(
    function Container({ children, reveal = true, replayKey }, ref) {
        return (
            <main
                ref={ref}
                className="vt-content mx-auto h-full max-w-container overflow-y-auto px-4"
                style={{
                    paddingTop:
                        "calc(max(env(safe-area-inset-top), var(--tg-content-top, 0px)) + var(--header-h) + 16px)",
                    paddingBottom:
                        "calc(max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + var(--nav-h) + var(--fab-lift) + 16px)",
                }}
            >
                <div
                    key={replayKey}
                    className={
                        reveal
                            ? "reveal-stagger flex flex-col gap-4"
                            : "flex flex-col gap-4"
                    }
                >
                    {children}
                </div>
            </main>
        );
    },
);
