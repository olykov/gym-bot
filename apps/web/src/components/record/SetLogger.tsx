/**
 * Phase B of the record flow — the set-logging panel (spec §12.3). The heart:
 * built so each set costs ~1 tap.
 *
 *  - One read: `GET /analytics/log-context` (GYM-71) → completed set numbers +
 *    the last prior session's sets + the PR, in a single round-trip.
 *  - Today recap = log-context completed set NUMBERS ∪ this-session saved sets
 *    (full w×r). Session sets show `Set n — {w}kg × {r}`; pre-session ones
 *    `Set n ✓`.
 *  - Auto set # = max(completed ∪ session) + 1 (never a naive counter).
 *  - Two pre-filled <Stepper>s, priority (§12.3): (1) this session's previous
 *    set for this exercise; (2) `last_session_sets` set N (what you did for that
 *    set last session); (3) empty + --hint, Save disabled until valid. PR is NOT
 *    a pre-fill source anymore — it's only the target chip.
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
import { useLogContext, useCreateTraining } from "@/hooks/useRecord";
import type { TrainingSet } from "@/api/training";
import type { ChosenExercise } from "./types";

/** A set logged in THIS session (full weight/reps, always exact). */
interface SessionSet {
    set: number;
    weight: number;
    reps: number;
}

interface SetLoggerProps {
    chosen: ChosenExercise;
    /** Today's date (YYYY-MM-DD) — the log-context / invalidation key. */
    today: string;
    /**
     * Today's already-logged sets for this exercise sourced from
     * `GET /training/day/{today}` — carries {set, weight, reps} so the recap
     * can show real values after reopen/Continue, not just ✓ (GYM-74).
     * The sheet may pass an empty array when the day hasn't loaded yet.
     */
    serverSets: TrainingSet[];
    onSwitch: () => void;
    onDone: () => void;
}

export function SetLogger({ chosen, today, serverSets, onSwitch, onDone }: SetLoggerProps) {
    const { muscleName, exerciseName } = chosen;

    const ctx = useLogContext(muscleName, exerciseName, today);
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

    const pr = ctx.data?.pr ?? null;

    // Server PR resolves once → seed the local anchor (don't clobber a session PR).
    useEffect(() => {
        if (pr && prAnchor === null) setPrAnchor(pr.weight);
    }, [pr, prAnchor]);

    // Reset everything when the chosen exercise changes (sheet re-used).
    useEffect(() => {
        setSessionSets([]);
        setPrAnchor(null);
        setPulse(false);
        setFlareSet(null);
        setWeightText("");
        setRepsText("");
    }, [muscleName, exerciseName]);

    // Auto set # = max(completed ∪ session) + 1 (§12.3, never a counter).
    const nextSet = useMemo(() => {
        const serverSets = ctx.data?.completed_sets ?? [];
        const sessionNums = sessionSets.map((s) => s.set);
        const all = [...serverSets, ...sessionNums];
        return (all.length ? Math.max(...all) : 0) + 1;
    }, [ctx.data, sessionSets]);

    // Pre-fill priority (§12.3): (1) this session's previous set for this
    // exercise; (2) last_session_sets for the NEXT set #; (3) leave empty (Save
    // disabled until valid). PR is NOT a pre-fill source. Only fills empty
    // fields so we never fight the user mid-edit. Runs as log-context resolves
    // and re-runs after each save (nextSet advances → next last-session set).
    const prefilledFor = useRef<string>("");
    useEffect(() => {
        const key = `${muscleName}/${exerciseName}/${nextSet}`;
        if (ctx.isLoading) return; // wait so the pre-fill isn't lost to empty.
        if (prefilledFor.current === key && (weightText || repsText)) return;

        const lastSession = sessionSets[sessionSets.length - 1];
        let w: number | null = null;
        let r: number | null = null;
        if (lastSession) {
            w = lastSession.weight;
            r = lastSession.reps;
        } else {
            const lastForSet = ctx.data?.last_session_sets.find(
                (s) => s.set === nextSet,
            );
            if (lastForSet) {
                w = lastForSet.weight;
                r = lastForSet.reps;
            }
        }
        prefilledFor.current = key;
        if (w != null && !weightText) setWeightText(String(w));
        if (r != null && !repsText) setRepsText(String(r));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [
        muscleName,
        exerciseName,
        nextSet,
        ctx.isLoading,
        ctx.data,
        sessionSets.length,
    ]);

    // Recap: union of all set numbers known today, with w×r sourced in priority:
    //  1. This-session set (always exact, was just logged).
    //  2. serverSets from GET /training/day/{today} (carries weight+reps from
    //     the server) — fixes the reopen/Continue ✓-only display (GYM-74).
    //  3. completed_sets from log-context (set numbers only, no w×r → shows ✓).
    const recap = useMemo(() => {
        const sessionByNum = new Map(sessionSets.map((s) => [s.set, s]));
        const serverByNum = new Map(serverSets.map((s) => [s.set, s]));
        const nums = new Set<number>([
            ...(ctx.data?.completed_sets ?? []),
            ...serverSets.map((s) => s.set),
            ...sessionSets.map((s) => s.set),
        ]);
        return [...nums]
            .sort((a, b) => a - b)
            .map((n) => {
                const session = sessionByNum.get(n) ?? null;
                // Server set provides w×r for pre-session sets (reopen / Continue).
                const srv = serverByNum.get(n);
                const weight = session?.weight ?? srv?.weight ?? null;
                const reps = session?.reps ?? srv?.reps ?? null;
                return {
                    set: n,
                    weight,
                    reps,
                };
            });
    }, [ctx.data, sessionSets, serverSets]);

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

    // The PR reps for the chip — held alongside the anchor weight so the chip
    // reads "PR {w}kg × {r}". Session PRs have no reps source, so the chip drops
    // the × part once the local anchor diverges from the server PR.
    const prReps = pr && prAnchor === pr.weight ? pr.reps : null;

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

            {/* Exercise identity (read-only, GYM-77 #2).
                The exercise name truncates at min-w-0 (the flex child clips).
                The muscle chip is shrink-0 with a max-width so it never
                overflows the row and still clips cleanly with an ellipsis. */}
            <div className="flex items-center gap-3">
                <h2 className="min-w-0 flex-1 truncate font-display text-title text-text" title={exerciseName}>
                    {exerciseName}
                </h2>
                <span className="shrink-0" style={{ maxWidth: "8rem" }}>
                    <Chip title={muscleName}>{muscleName}</Chip>
                </span>
            </div>

            {/* Today recap — log-context numbers ∪ this-session w×r (§12.3). */}
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
                                {row.weight !== null && row.reps !== null ? (
                                    <span className="tabular font-display text-title leading-none text-text">
                                        {row.weight}kg × {row.reps}
                                    </span>
                                ) : (
                                    <span className="text-base text-hint">✓</span>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* SET heading + PR target chip (§12.3) — "PR {w}kg × {r}". */}
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
                        {prReps !== null ? ` × ${prReps}` : ""}
                    </span>
                ) : null}
            </div>

            {ctx.isLoading ? (
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
