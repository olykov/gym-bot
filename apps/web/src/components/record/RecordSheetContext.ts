/**
 * Minimal record-sheet opener context (GYM-118).
 *
 * The sheet's open STATE keeps living in <AppShell> (the FAB's `onRecord` prop
 * path through <BottomNav> is unchanged); this context only exposes an
 * imperative `openRecordSheet()` so pages — concretely the empty-state CTAs on
 * Dashboard / Progress / History — can launch the record flow without
 * prop-drilling through the router. One value + one hook; no store library.
 */
import { createContext, useContext } from "react";

export interface RecordSheetContextValue {
    /** Open the shell-owned record sheet (same path as the center FAB). */
    openRecordSheet: () => void;
}

export const RecordSheetContext = createContext<RecordSheetContextValue | null>(
    null,
);

/**
 * The record-sheet opener for pages. Every data page renders inside
 * <AppShell>'s provider, so a missing provider is a wiring bug — fail fast.
 *
 * @returns the context value with `openRecordSheet()`.
 */
export function useRecordSheet(): RecordSheetContextValue {
    const ctx = useContext(RecordSheetContext);
    if (!ctx) {
        throw new Error(
            "useRecordSheet must be used inside AppShell's RecordSheetContext provider",
        );
    }
    return ctx;
}
