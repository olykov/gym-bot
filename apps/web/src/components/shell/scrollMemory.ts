/**
 * In-memory per-entry scroll positions (GYM-116).
 *
 * Keyed by react-router's `location.key`, so every history entry remembers its
 * own offset (visiting /history twice via different pushes = two entries = two
 * positions). Deliberately session-scoped (no sessionStorage): Telegram Mini
 * Apps restart with a fresh history stack, so persisted keys could never match
 * again. Pure module — no React, no DOM — so the logic is unit-testable.
 */

export interface ScrollStore {
    /** Remember the scroll offset for a history entry. */
    save(key: string, top: number): void;
    /** Offset previously saved for the entry, or 0 (top) when unseen. */
    restore(key: string): number;
}

/** Create an isolated store (the app uses one module-level instance). */
export function createScrollStore(): ScrollStore {
    const positions = new Map<string, number>();

    return {
        save(key: string, top: number): void {
            // Guard against NaN/negative from exotic WebView scroll reads.
            positions.set(key, Number.isFinite(top) && top > 0 ? top : 0);
        },
        restore(key: string): number {
            return positions.get(key) ?? 0;
        },
    };
}
