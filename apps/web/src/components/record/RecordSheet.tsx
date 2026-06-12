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
 * GYM-74: The sheet is fixedHeight so it never jumps between Phase A's two
 * picker steps. The picker step state is lifted here so the BackButton override
 * can navigate picker-step-back before closing the sheet. While the picker is on
 * the exercise step, Back → muscles step; on the muscle step → close sheet.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useT } from "@/i18n/catalog";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { RecordPicker } from "./RecordPicker";
import { SetLogger } from "./SetLogger";
import { SessionSummaryPanel } from "./SessionSummaryPanel";
import { toISODate } from "@/components/history/historyWindow";
import { useTrainingDay } from "@/hooks/useTraining";
import type { TrainingSet } from "@/api/training";
import type { ChosenExercise } from "./types";
import type { SessionLogEntry } from "./derive";

/** Which step Phase A is currently on (GYM-74 slide-nav). */
export type PickerStep = "muscles" | "exercises";

interface RecordSheetProps {
    open: boolean;
    onClose: () => void;
}

export function RecordSheet({ open, onClose }: RecordSheetProps) {
    const { t } = useT();
    const [chosen, setChosen] = useState<ChosenExercise | null>(null);
    /**
     * GYM-85: transient hint shown after resolution=existing on create, persists
     * through the Phase A→B transition so it is visible in SetLogger. Cleared on
     * sheet close or on the next add action.
     */
    const [createHint, setCreateHint] = useState<string | null>(null);
    const today = toISODate(new Date());

    // Phase A picker step — lifted here so the BackButton override can step back
    // from exercises → muscles before allowing the sheet to close.
    const [pickerStep, setPickerStep] = useState<PickerStep>("muscles");

    /**
     * GYM-77 #4 — selectedMuscle is lifted OUT of RecordPicker so it survives
     * the Phase A ↔ Phase B round-trip. Without this, when the user adds a new
     * exercise (auto-selects into Phase B) and then presses "← Switch exercise"
     * (onSwitch → setChosen(null)), RecordPicker remounts with its local
     * selectedMuscle reset to null → the exercise step shows an empty panel.
     *
     * With the state lifted here:
     *  - pickMuscle / goBack call onMuscleChange → this state updates.
     *  - onSwitch (Phase B → A) → setChosen(null) but selectedMuscle stays.
     *  - The Telegram BackButton on the exercise step → pickerStepRef "exercises"
     *    → setPickerStep("muscles") + setSelectedMuscle(null) (full reset).
     *  - On sheet close → full reset (muscles step + null muscle).
     */
    const [selectedMuscle, setSelectedMuscle] = useState<string | null>(null);

    // Stable ref so the BackButton override closure doesn't go stale.
    const pickerStepRef = useRef<PickerStep>("muscles");
    pickerStepRef.current = pickerStep;

    /**
     * GYM-132: the cross-exercise session log — every set saved while this
     * sheet is open, across ALL exercises (SetLogger's own sessionSets reset
     * on exercise switch; this one survives). A ref, not state: appends must
     * not re-render the sheet mid-logging; the summary reads it on Done.
     */
    const sessionLogRef = useRef<SessionLogEntry[]>([]);
    const handleSetLogged = useCallback((entry: SessionLogEntry) => {
        sessionLogRef.current = [...sessionLogRef.current, entry];
    }, []);

    /**
     * GYM-132: summary body-swap flag. Set ONLY by the explicit Done button
     * (scrim / Telegram Back / drag-dismiss keep closing directly, as
     * before). With an empty session log Done closes immediately — the
     * summary never appears, the fast path is untouched.
     */
    const [showSummary, setShowSummary] = useState(false);
    const handleDone = useCallback(() => {
        if (sessionLogRef.current.length > 0) setShowSummary(true);
        else onClose();
    }, [onClose]);

    // Fetch today's training to source server sets (w×r) for the recap (GYM-74).
    const day = useTrainingDay(today);

    // Reset to Phase A every time the sheet closes, so the next open is fresh.
    useEffect(() => {
        if (!open) {
            setChosen(null);
            setPickerStep("muscles");
            setSelectedMuscle(null);
            setCreateHint(null);
            // GYM-132: a new sheet open is a new session.
            setShowSummary(false);
            sessionLogRef.current = [];
        }
    }, [open]);

    // BackButton override: while on the exercise step, Back → muscles (not close).
    const handleBackOverride = useCallback((): boolean => {
        // Only intercept when Phase A is on the exercise step.
        if (!chosen && pickerStepRef.current === "exercises") {
            setPickerStep("muscles");
            setSelectedMuscle(null);
            return true; // consumed — do not close the sheet
        }
        return false; // let the sheet close
    }, [chosen]);

    // Today's sets for the chosen exercise (w×r) — sourced from day detail.
    // Passed to SetLogger so the recap shows real values after reopen/Continue.
    const serverSets: TrainingSet[] = chosen
        ? (day.data?.exercises.find(
              (ex) =>
                  ex.exercise_name === chosen.exerciseName &&
                  ex.muscle_name === chosen.muscleName,
          )?.sets ?? [])
        : [];

    return (
        <BottomSheet
            open={open}
            onClose={onClose}
            titleId="record-sheet-title"
            fixedHeight
            onBackOverride={handleBackOverride}
        >
            <div id="record-sheet-title" className="sr-only">
                {t("nav.recordTraining")}
            </div>
            {showSummary ? (
                // GYM-132: the closing moment — same sheet, body-swapped like
                // Phase A↔B. One tap anywhere (or ~4s, scrim, Back) → the
                // SAME onClose as every other close path (§12.5 unchanged).
                <SessionSummaryPanel
                    log={sessionLogRef.current}
                    onDismiss={onClose}
                />
            ) : chosen ? (
                <SetLogger
                    chosen={chosen}
                    today={today}
                    serverSets={serverSets}
                    createHint={createHint}
                    onClearCreateHint={() => setCreateHint(null)}
                    onSwitch={() => {
                        // GYM-77 #4: return to the exercise list for the same
                        // muscle (selectedMuscle is preserved here in the
                        // controller, so RecordPicker remounts with the right
                        // muscle and the picker step stays on "exercises").
                        setChosen(null);
                        setCreateHint(null);
                    }}
                    onDone={handleDone}
                    onSetLogged={handleSetLogged}
                />
            ) : (
                <RecordPicker
                    today={today}
                    step={pickerStep}
                    onStepChange={setPickerStep}
                    selectedMuscle={selectedMuscle}
                    onMuscleChange={setSelectedMuscle}
                    onPick={setChosen}
                    onCreateHint={setCreateHint}
                />
            )}
        </BottomSheet>
    );
}
