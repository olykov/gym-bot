/**
 * The single content container (spec §2 / §10.1). The ONLY place page content
 * mounts: one max-width (~480px), one horizontal padding (16px), one vertical
 * rhythm. It owns the scroll model — only this area scrolls, with top/bottom
 * padding clearing the fixed header and bottom-nav. The clearance uses
 * max(env(safe-area-inset-*), var(--tg-*)) so it accounts for Telegram's
 * fullscreen content-safe inset (Bot API 8.0) AND the device notch/home
 * indicator in fullsize/browser (spec §4).
 *
 * It also applies the page-load reveal stagger (spec §9.4): direct children are
 * faded+risen with an incrementing --reveal-i, gated by prefers-reduced-motion.
 * Pass a `revealKey` (e.g. the route) so the stagger replays on navigation.
 */
import { Children, isValidElement, cloneElement, type ReactNode } from "react";

interface ContainerProps {
    children: ReactNode;
    /** Changing this re-keys the children so the reveal replays per route. */
    revealKey?: string;
}

export function Container({ children, revealKey }: ContainerProps) {
    return (
        <main
            key={revealKey}
            className="mx-auto h-full max-w-container overflow-y-auto px-4"
            style={{
                paddingTop:
                    "calc(max(env(safe-area-inset-top), var(--tg-content-top, 0px)) + var(--header-h) + 16px)",
                paddingBottom:
                    "calc(max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)) + var(--nav-h) + 16px)",
            }}
        >
            <div className="flex flex-col gap-4">
                {Children.map(children, (child, i) =>
                    isValidElement(child)
                        ? cloneElement(child, {
                              // Tag each direct child for the staggered reveal.
                              className: `reveal ${
                                  (child.props as { className?: string }).className ?? ""
                              }`.trim(),
                              style: {
                                  ...(child.props as { style?: object }).style,
                                  ["--reveal-i" as string]: i,
                              },
                          } as Partial<Record<string, unknown>>)
                        : child,
                )}
            </div>
        </main>
    );
}
