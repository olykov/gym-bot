/**
 * Phase B of the record flow — the set-logging panel (spec §12.3). The heart:
 * built so each set costs ~1 tap.
 *
 *  - Today recap = `completed-sets` set NUMBERS ∪ this-session saved sets (full
 *    w×r). Session sets show `Set n — {w}kg × {r}`; pre-session ones `Set n ✓`.
 *  - Auto set # = max(completed-sets ∪ session) + 1 (never a naive counter).
 *  - Two pre-filled <Stepper>s, priority: (1) same-session last set for this
 *    exercise; (2) the carried recent last working set (or PR fallback); (3)
 *    empty + --hint, Save disabled until valid.
 *  - In-sheet sticky <SheetSaveButton> → `POST /training`. On success: success
 *    haptic, append to recap (optimistic), re-arm in place (nextSet+1, same
 *    pre-fill) → +1 tap/set. PR-beat: a single accent pulse when the weight
 *    strictly beats the known PR, behind prefers-reduced-motion.
 *  - "← Switch exercise" → Phase A; "Done" → close (controller invalidates).
 *
 * Write error (§12.5): keep the sheet open, surface an inline message, do NOT
 * advance the set number or append the recap (the recap never lies).
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { Stepper, parseNumeric } from "@/components/ui/Stepper";
import { SheetSaveButton } from "@/components/ui/SheetSaveButton";
import { hapticNotification } from "@/telegram/webapp";
import {
    useCompletedSets,
    usePersonalRecord,
    useCreateTraining,
} from "@/hooks/useRecord";
import type { ChosenExercise } from "./types";

/** A set logged in THIS session (full weight/reps, always exact). */
interface SessionSet {
    set: number;
    weight: number;
    reps: number;
}

interface SetLoggerProps {
    chosen: ChosenExercise;
    /** Today's date (YYYY-MM-DD) — the completed-sets / invalidation key. */
    today: string;
    onSwitch: () => void;
    onDone: () => void;
}

export function SetLogger({ chosen, today, onSwitch, onDone }: SetLoggerProps) {
    const { muscleName, exerciseName } = chosen;

    const completed = useCompletedSets(muscleName, exerciseName, today);
    const pr = usePersonalRecord(muscleName, exerciseName);
    const create = useCreateTraining(today);

    // Sets logged this session for THIS exercise (optimistic recap source).
    const [sessionSets, setSessionSets] = useState<SessionSet[]>([]);
    // The PR weight anchor — updated locally so a second PR also celebrates.
    const [prAnchor, setPrAnchor] = useState<number | null>(null);
    // PR-beat flare: the recap-row index to flare + a pulse on the Save button.
    const [pulse, setPulse] = useState(false);
    const [flareSet, setFlareSet] = useState<number | null>(null);

    // The just-typed/stepped values (raw text + parsed).
    const [weightText, setWeightText] = useState("");
    const [repsText, setRepsText] = useState("");
    const weight = parseNumeric(weightText, false);
    const reps = parseNumeric(repsText, true);

    // Server PR resolves once → seed the local anchor (don't clobber a session PR).
    useEffect(() => {
        if (pr.data && prAnchor === null) setPrAnchor(pr.data.weight);
    }, [pr.data, prAnchor]);

    // Reset everything when the chosen exercise changes (sheet re-used).
    useEffect(() => {
        setSessionSets([]);
        setPrAnchor(null);
        setPulse(false);
        setFlareSet(null);
        setWeightText("");
        setRepsText("");
    }, [muscleName, exerciseName]);

    // Pre-fill priority (§12.3): (1) same-session last set; (2) carried recent
    // last working set, else PR; (3) leave empty. Only fills empty fields so we
    // never fight the user mid-edit. Runs as the inputs resolve.
    const prefilledFor = useRef<string>("");
    useEffect(() => {
        const key = `${muscleName}/${exerciseName}`;
        // Wait for the per-exercise reads so a slow PR doesn't lose to empty.
        if (completed.isLoading || pr.isLoading) return;
        if (prefilledFor.current === key && (weightText || repsText)) return;

        const lastSession = sessionSets[sessionSets.length - 1];
        let w: number | null = null;
        let r: number | null = null;
        if (lastSession) {
            w = lastSession.weight;
            r = lastSession.reps;
        } else if (chosen.lastWeight != null && chosen.lastReps != null) {
            w = chosen.lastWeight;
            r = chosen.lastReps;
        } else if (pr.data) {
            w = pr.data.weight;
            r = pr.data.reps;
        }
        prefilledFor.current = key;
        if (w != null && !weightText) setWeightText(String(w));
        if (r != null && !repsText) setRepsText(String(r));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [
        muscleName,
        exerciseName,
        completed.isLoading,
        pr.isLoading,
        pr.data,
        sessionSets.length,
    ]);

    // Auto set # = max(completed-sets ∪ session) + 1 (§12.3, never a counter).
    const nextSet = useMemo(() => {
        const serverSets = completed.data?.sets ?? [];
        const sessionNums = sessionSets.map((s) => s.set);
        const all = [...serverSets, ...sessionNums];
        return (all.length ? Math.max(...all) : 0) + 1;
    }, [completed.data, sessionSets]);

    // Recap: server set numbers (✓ only) ∪ this-session sets (full w×r).
    const recap = useMemo(() => {
        const sessionByNum = new Map(sessionSets.map((s) => [s.set, s]));
        const nums = new Set<number>([
            ...(completed.data?.sets ?? []),
            ...sessionSets.map((s) => s.set),
        ]);
        return [...nums]
            .sort((a, b) => a - b)
            .map((n) => ({ set: n, session: sessionByNum.get(n) ?? null }));
    }, [completed.data, sessionSets]);

    const valid =
        weight !== null && weight >= 0 && reps !== null && reps >= 0;
    const canSave = valid && !create.isPending;

    function save(): void {
        if (!canSave || weight === null || reps === null) return;
        const set = nextSet;
        create.mutate(
            { muscle_name: muscleName, exercise_name: exerciseName, set, weight, reps },
            {
                onSuccess: () => {
                    hapticNotification("success");
                    // Append to recap (optimistic) + re-arm in place (§12.3).
                    setSessionSets((prev) => [...prev, { set, weight, reps }]);
                    // PR-beat: strictly beats the known anchor (or first ever).
                    const beat = prAnchor === null || weight > prAnchor;
                    if (beat) {
                        setPrAnchor(weight);
                        setPulse(true);
                        setFlareSet(set);
                        window.setTimeout(() => {
                            setPulse(false);
                            setFlareSet(null);
                        }, 700);
                    }
                    // Keep the same pre-fill (gym sets repeat); Save re-enabled.
                },
            },
        );
    }

    const loadingNumbers = completed.isLoading || pr.isLoading;

    return (
        <div className="pb-2">
            {/* Switch-exercise (in-body, NOT the Telegram Back — §12.8). */}
            <button
                type="button"
                onClick={onSwitch}
                className="press-95 -ml-1 mb-3 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
            >
                ← Switch exercise
            </button>

            {/* Exercise identity (read-only). */}
            <div className="flex items-center gap-3">
                <h2 className="min-w-0 truncate font-display text-title text-text">
                    {exerciseName}
                </h2>
                <Chip>{muscleName}</Chip>
            </div>

            {/* Today recap — completed-sets numbers ∪ this-session w×r (§12.3). */}
            <section className="mt-5">
                <div className="text-label uppercase tracking-wide text-hint">
                    Today
                </div>
                {recap.length === 0 ? (
                    <p className="mt-2 text-base text-hint">No sets logged yet.</p>
                ) : (
                    <div className="mt-2 flex flex-col divide-y divide-hairline">
                        {recap.map((row) => (
                            <div
                                key={row.set}
                                className={`flex min-h-[36px] items-center justify-between gap-4 ${
                                    flareSet === row.set
                                        ? "pr-flare motion-reduce:animate-none"
                                        : ""
                                }`}
                            >
                                <span className="text-label uppercase tracking-wide text-hint">
                                    Set {row.set}
                                </span>
                                {row.session ? (
                                    <span className="tabular font-display text-title leading-none text-text">
                                        {row.session.weight}kg × {row.session.reps}
                                    </span>
                                ) : (
                                    <span className="text-base text-hint">✓</span>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* SET heading + PR target chip (§12.3). */}
            <div className="mt-6 flex items-center justify-between">
                <h3 className="font-display text-title text-text">
                    SET {nextSet}
                </h3>
                {prAnchor !== null ? (
                    <span
                        className={`tabular rounded-full px-3 py-1 text-label font-semibold text-accent ${
                            pulse ? "pr-pulse motion-reduce:animate-none" : ""
                        }`}
                    >
                        PR {prAnchor}kg
                    </span>
                ) : null}
            </div>

            {loadingNumbers ? (
                <p className="mt-2 text-label text-hint">loading your numbers…</p>
            ) : null}

            {/* Two pre-filled steppers (§12.3). */}
            <div className="mt-4 flex flex-col gap-6">
                <Stepper
                    label="Weight"
                    unit="kg"
                    value={weight}
                    text={weightText}
                    onChange={({ text }) => setWeightText(text)}
                    min={0}
                    step={2.5}
                    inputMode="decimal"
                />
                <Stepper
                    label="Reps"
                    value={reps}
                    text={repsText}
                    onChange={({ text }) => setRepsText(text)}
                    min={0}
                    step={1}
                    integer
                    inputMode="numeric"
                />
            </div>

            {/* Write error (§12.5) — sheet stays open, no recap was appended. */}
            {create.isError ? (
                <p className="mt-3 text-label text-accent">
                    Couldn't save that set — try again.
                </p>
            ) : null}

            {/* Sticky in-sheet SAVE — the shared <SheetSaveButton> (§11.4). */}
            <SheetSaveButton
                label={`Save set ${nextSet}`}
                onClick={save}
                disabled={!canSave}
                pulse={pulse}
            />

            {/* Quiet "finish" affordance — closes the sheet (§12.3). */}
            <button
                type="button"
                onClick={onDone}
                className="press-95 mt-2 min-h-[44px] w-full text-base text-hint"
            >
                Done
            </button>
        </div>
    );
}
