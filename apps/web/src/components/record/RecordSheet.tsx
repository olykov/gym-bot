/**
 * The record-flow controller (spec §12.2 / §12.4). Composes the existing
 * <BottomSheet> and swaps its body between Phase A (<RecordPicker>) and Phase B
 * (<SetLogger>) — a body-swap, NOT a multi-route wizard, so auto-advance feels
 * like staying in place and the §11.4 in-sheet sticky Save is preserved.
 *
 * Opened by the NavFab's `onRecord` (GYM-68 → wired from the shell). The
 * <BottomSheet> already owns the BackButton rule (§11.7): while open, the
 * Telegram BackButton closes the SHEET first. Inside, "← Switch exercise" is an
 * in-body control (B→A); Back always closes the whole sheet (one predictable
 * back-step), it does not step B→A (§12.8).
 *
 * Cross-screen invalidation (§12.5) fires per save-settle inside
 * useCreateTraining, so by the time the sheet closes every dependent screen
 * (Dashboard / Progress / History) has already been marked stale.
 */
import { useEffect, useState } from "react";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { RecordPicker } from "./RecordPicker";
import { SetLogger } from "./SetLogger";
import { toISODate } from "@/components/history/historyWindow";
import type { ChosenExercise } from "./types";

interface RecordSheetProps {
    open: boolean;
    onClose: () => void;
}

export function RecordSheet({ open, onClose }: RecordSheetProps) {
    const [chosen, setChosen] = useState<ChosenExercise | null>(null);
    const today = toISODate(new Date());

    // Reset to Phase A every time the sheet closes, so the next open is fresh.
    useEffect(() => {
        if (!open) setChosen(null);
    }, [open]);

    return (
        <BottomSheet open={open} onClose={onClose} titleId="record-sheet-title">
            <div id="record-sheet-title" className="sr-only">
                Record training
            </div>
            {chosen ? (
                <SetLogger
                    chosen={chosen}
                    today={today}
                    onSwitch={() => setChosen(null)}
                    onDone={onClose}
                />
            ) : (
                <RecordPicker today={today} onPick={setChosen} />
            )}
        </BottomSheet>
    );
}
