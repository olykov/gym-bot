/**
 * Phase B of the record flow — the set-logging panel (spec §12.3). The heart:
 * built so each set costs ~1 tap.
 *
 *  - One read: `GET /analytics/log-context` (GYM-71) → completed set numbers +
 *    the last prior session's sets + the PR, in a single round-trip.
 *  - Recap (GYM-130) = a TODAY | LAST TIME comparison matched by set number,
 *    ASC (Set 1 top — line-by-line reading; reverts the GYM-101 DESC order).
 *    Today figures keep the priority session > server > ✓-only (`— · —`,
 *    GYM-123 #3 — honest, never fabricated); last-session-only rows are
 *    GHOSTS (--hint, ~70% opacity) — the visible target. Saved sets that
 *    match a ghost get a delta (weight first, reps tiebreak). With no prior
 *    session the recap renders single-column exactly as before. "Last set
 *    visible" is solved by auto-scrolling the recap to the just-saved row
 *    (and to the next ghost target on entry).
 *  - Auto set # = max(completed ∪ session) + 1 (never a naive counter).
 *  - Two pre-filled <Stepper>s, priority (§12.3): (1) this session's previous
 *    set for this exercise; (2) `last_session_sets` set N (what you did for that
 *    set last session); (3) empty + --hint, Save disabled until valid. PR is NOT
 *    a pre-fill source anymore — it's only the target chip.
 *  - In-sheet sticky <SheetSaveButton> → `POST /training`. On success: success
 *    haptic, append to recap (optimistic), re-arm in place (nextSet+1, same
 *    pre-fill) → +1 tap/set. PR-beat (GYM-133): one resolved kind per save —
 *    weight PR = full celebration (banner + pulse + flare); reps-at-weight /
 *    e1rm PRs are quiet (no banner). All behind prefers-reduced-motion.
 *  - GYM-135: the SET/PR heading row (SetHeadingRow.tsx) carries a secondary
 *    e1RM trend sparkline + chip (TrendSparkline owns its own read).
 *  - "← Switch exercise" → Phase A; "Done" → RecordSheet (summary or close).
 *  - GYM-131 save choreography: row entrance + soft flash, delta slide-in,
 *    Save success morph, SET digit roll, PR banner — all CSS-token motion
 *    behind prefers-reduced-motion, timers in useSaveChoreography.
 *  - GYM-132: each saved set is reported up via onSetLogged (beat-last /
 *    beat-PR computed here) — RecordSheet owns the session log + summary.
 *
 * Layout (GYM-101): the root div is a flex column that fills the sheet body.
 *   - Static top: switch button + createHint + exercise identity (shrink-0).
 *   - Recap region: internally scrollable (flex-1 min-h-0 overflow-y-auto),
 *     so older sets scroll away without pushing the controls down.
 *   - Controls region: always-visible (shrink-0) — SET heading + PR chip +
 *     loading hint + steppers + error + SheetSaveButton + Done.
 * The page/sheet itself never scrolls; only the recap block scrolls internally.
 *
 * Write error (§12.5): keep the sheet open, surface an inline message, do NOT
 * advance the set number or append the recap (the recap never lies).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useT } from "@/i18n/catalog";
import { Chip } from "@/components/ui/Chip";
import { Stepper } from "@/components/ui/Stepper";
import { SheetSaveButton } from "@/components/ui/SheetSaveButton";
import { hapticImpact, hapticNotification } from "@/telegram/webapp";
import { useLogContext, useCreateTraining } from "@/hooks/useRecord";
import { useWeightRepsForm } from "@/hooks/useWeightRepsForm";
import type { TrainingSet } from "@/api/training";
import type { ChosenExercise } from "./types";
import { ComparisonRecap } from "./ComparisonRecap";
import { PrBannerOverlay } from "./PrBannerOverlay";
import { SetHeadingRow } from "./SetHeadingRow";
import { useSaveChoreography } from "./useSaveChoreography";
import {
    beatsLastSession,
    buildComparisonRows,
    computeEffectivePR,
    computeNextSet,
    derivePrefill,
    findNextGhostSet,
    resolvePrBeat,
    saveErrorMessage,
    type SessionLogEntry,
    type SessionSet,
} from "./derive";

/** Reduced-motion check for the recap auto-scroll (instant vs smooth). */
function prefersReducedMotion(): boolean {
    return (
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
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
    /**
     * GYM-85: non-blocking hint from the add-inline resolution=existing path.
     * Shows "You already have 'Name'." below the switch button. Null when no hint.
     * Persisted in RecordSheet (controller) so it survives the Phase A→B unmount.
     */
    createHint?: string | null;
    /**
     * GYM-85: called when the user dismisses the create hint (or whenever it
     * should be cleared — e.g. on switch). RecordSheet owns the hint state.
     */
    onClearCreateHint?: () => void;
    onSwitch: () => void;
    onDone: () => void;
    /**
     * GYM-132: reports every successfully saved set (with its beat-last /
     * beat-PR flags, computed here at save time) to RecordSheet, which owns
     * the cross-exercise session log behind the Done summary.
     */
    onSetLogged: (entry: SessionLogEntry) => void;
}

export function SetLogger({ chosen, today, serverSets, createHint, onClearCreateHint, onSwitch, onDone, onSetLogged }: SetLoggerProps) {
    const { t, muscle } = useT();
    const { muscleName, exerciseName } = chosen;

    const ctx = useLogContext(muscleName, exerciseName, today);
    const create = useCreateTraining(today);

    // Sets logged this session for THIS exercise (optimistic recap source).
    const [sessionSets, setSessionSets] = useState<SessionSet[]>([]);
    // GYM-131: every transient save celebration (success morph, PR pulse /
    // row flare, PR banner) + its interrupt-safe timers live in one hook.
    const { pulse, flareSet, morph, banner, onSave, reset: resetChoreo } =
        useSaveChoreography();

    // The just-typed/stepped values (raw text + parsed) — shared form
    // mechanics (GYM-126); the §12.3 pre-fill effect below stays local.
    const form = useWeightRepsForm();
    const {
        weightText,
        repsText,
        setWeightText,
        setRepsText,
        weight,
        reps,
        reset,
    } = form;

    const serverPR = ctx.data?.pr ?? null;

    /**
     * GYM-104 #3: DERIVED effective PR — no race (rationale in derive.ts).
     * Renders the PR chip; resolvePrBeat (GYM-133) derives the same value
     * from the same inputs for the weight-PR check at save time.
     */
    const effectivePR = useMemo(
        () => computeEffectivePR(serverPR, sessionSets),
        [serverPR, sessionSets],
    );

    // Reset everything when the chosen exercise changes (sheet re-used).
    // form.reset / resetChoreo are identity-stable (useCallback), so they
    // never re-trigger this effect.
    useEffect(() => {
        setSessionSets([]);
        resetChoreo();
        reset();
    }, [muscleName, exerciseName, reset, resetChoreo]);

    // Auto set # = max(completed ∪ session) + 1 (§12.3, never a counter).
    const nextSet = useMemo(
        () => computeNextSet(ctx.data?.completed_sets ?? [], sessionSets),
        [ctx.data, sessionSets],
    );

    // Pre-fill priority (§12.3, GYM-152): (1) last_session_sets matched by the
    // current set number (last training's set N); (2) repeat this session's
    // last set (more sets than last time / new exercise); (3) leave empty (Save
    // disabled until valid). PR is NOT a pre-fill source.
    //
    // GYM-152b: when the set number changes (a save advanced nextSet, or the
    // exercise switched) we OVERWRITE the fields with the new set's pre-fill —
    // otherwise the previous set's values linger and block the new pre-fill
    // (continuous logging: save set 1 → set 2 must re-arm with last training's
    // set 2, not keep set 1's numbers). Within the SAME set we never fight the
    // user: if they've typed anything we leave it; if it's still empty we fill
    // (catches last-session data that resolves late, e.g. by name_key).
    const prefilledFor = useRef<string>("");
    useEffect(() => {
        const key = `${muscleName}/${exerciseName}/${nextSet}`;
        if (ctx.isLoading) return; // wait so the pre-fill isn't lost to empty.
        const isNewSet = prefilledFor.current !== key;
        if (!isNewSet && (weightText || repsText)) return; // same set, user typing

        const { weight: w, reps: r } = derivePrefill(
            nextSet,
            sessionSets,
            ctx.data?.last_session_sets ?? [],
        );
        prefilledFor.current = key;
        setWeightText(w != null ? String(w) : "");
        setRepsText(r != null ? String(r) : "");
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [
        muscleName,
        exerciseName,
        nextSet,
        ctx.isLoading,
        ctx.data,
        sessionSets.length,
    ]);

    // Recap (GYM-130): TODAY | LAST TIME comparison rows matched by set
    // number, ASC. Today column keeps priority session > server > ✓-only;
    // last-session-only rows are ghosts — algorithm in derive.ts.
    const lastSessionSets = ctx.data?.last_session_sets ?? [];
    const recap = useMemo(
        () =>
            buildComparisonRows(
                ctx.data?.completed_sets ?? [],
                serverSets,
                sessionSets,
                ctx.data?.last_session_sets ?? [],
            ),
        [ctx.data, serverSets, sessionSets],
    );
    const hasGhost = lastSessionSets.length > 0;

    // GYM-130 auto-scroll plumbing: each recap row registers its element by
    // set number so the effects below can scrollIntoView a specific row
    // inside the internally-scrollable recap region.
    const rowEls = useRef<Map<number, HTMLDivElement>>(new Map());
    const registerRow = useCallback(
        (set: number, el: HTMLDivElement | null) => {
            if (el) rowEls.current.set(set, el);
            else rowEls.current.delete(set);
        },
        [],
    );

    // After a save appends a row at the bottom (ASC), keep the just-saved
    // row visible. block:"nearest" no-ops when already in view; smooth is
    // gated behind prefers-reduced-motion (then: instant).
    const lastSaved = sessionSets[sessionSets.length - 1];
    const lastSavedSet = lastSaved ? lastSaved.set : null;
    useEffect(() => {
        if (lastSavedSet === null) return;
        rowEls.current.get(lastSavedSet)?.scrollIntoView({
            block: "nearest",
            behavior: prefersReducedMotion() ? "auto" : "smooth",
        });
    }, [lastSavedSet]);

    // On Phase-B entry (per exercise, once log-context resolves): bring the
    // NEXT ghost target — the first unlogged last-session set — into view if
    // the rows overflow the recap region. Instant (it's an initial position,
    // not a transition).
    const ghostScrolledFor = useRef<string>("");
    useEffect(() => {
        const key = `${muscleName}/${exerciseName}`;
        if (!ctx.data || ghostScrolledFor.current === key) return;
        ghostScrolledFor.current = key;
        const target = findNextGhostSet(recap);
        if (target === null) return;
        rowEls.current
            .get(target)
            ?.scrollIntoView({ block: "nearest", behavior: "auto" });
    }, [ctx.data, recap, muscleName, exerciseName]);

    const canSave = form.valid && !create.isPending;

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
                    // GYM-133: ONE PR-beat kind per save (weight > reps-at-
                    // weight > e1rm), resolved against the PRE-save session
                    // sets; the weight branch keeps the GYM-104 derived-
                    // effective-PR check verbatim (race-free).
                    const last = ctx.data?.last_session_sets ?? [];
                    const saved = { set, weight, reps };
                    const prBeat = resolvePrBeat(serverPR, last, sessionSets, saved);
                    // GYM-131: morph/pulse/flare — interrupt-safe; the banner
                    // fires for the weight kind only (GYM-133 calibration).
                    onSave({ set, weight, reps, prBeat });
                    // GYM-132: report to RecordSheet's session log; beat-last
                    // = GYM-130 delta vs the same-number ghost, at save time.
                    // beatPR stays WEIGHT-PRs-only ("{n} PR" count unchanged).
                    onSetLogged({
                        muscle: muscleName,
                        exercise: exerciseName,
                        set,
                        weight,
                        reps,
                        beatLast: beatsLastSession(last, saved),
                        beatPR: prBeat === "weight",
                    });
                    // nextSet now advances → the pre-fill effect re-arms the
                    // fields with the NEXT set's pre-fill (GYM-152b). Save re-enabled.
                },
            },
        );
    }

    return (
        // GYM-101: root is a flex column that fills the sheet body (the sheet
        // body is already flex-col + overflow-y:auto from BottomSheet fixedHeight
        // mode). By making this element flex-col flex-1 min-h-0, the three
        // regions below can distribute the available height correctly:
        //   1. Static top  — shrink-0, always at the top
        //   2. Recap       — flex-1 min-h-0 overflow-y-auto, consumes remaining space
        //   3. Controls    — shrink-0, always at the bottom (never pushed off-screen)
        <div className="relative flex min-h-0 flex-1 flex-col">
            {/* GYM-131 #5: PR banner overlay (lives in PrBannerOverlay.tsx). */}
            <PrBannerOverlay banner={banner} />

            {/* ── Static top: switch + createHint + exercise identity ──────── */}
            <div className="shrink-0">
                {/* Switch-exercise (in-body, NOT the Telegram Back — §12.8). */}
                <button
                    type="button"
                    onClick={onSwitch}
                    className="press-95 -ml-1 mb-3 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
                >
                    ← {t("logger.switchExercise")}
                </button>

                {/* GYM-85: non-blocking hint when resolution=existing on the previous
                    add-inline action. Shown only once; dismissed by the × or naturally
                    when the user switches exercises. Tokens only — text-hint (muted). */}
                {createHint ? (
                    <div className="mb-3 flex items-center justify-between gap-2 rounded-md border border-hairline bg-secondary-bg px-3 py-2">
                        <p
                            aria-live="polite"
                            className="text-label text-hint"
                        >
                            {createHint}
                        </p>
                        <button
                            type="button"
                            aria-label={t("common.dismiss")}
                            onClick={onClearCreateHint}
                            className="press-95 flex shrink-0 min-h-[32px] min-w-[32px] items-center justify-center text-base text-hint"
                        >
                            ×
                        </button>
                    </div>
                ) : null}

                {/* Exercise identity (read-only, GYM-77 #2).
                    The exercise name truncates at min-w-0 (the flex child clips).
                    The muscle chip is shrink-0 with a max-width so it never
                    overflows the row and still clips cleanly with an ellipsis. */}
                <div className="flex items-center gap-3">
                    <h2 className="min-w-0 flex-1 truncate font-display text-title text-text" title={exerciseName}>
                        {exerciseName}
                    </h2>
                    <span className="min-w-0 max-w-chip shrink-0">
                        <Chip title={muscle(muscleName)}>
                            {muscle(muscleName)}
                        </Chip>
                    </span>
                </div>
            </div>

            {/* ── Recap region: internally scrollable, bounded by remaining height ── */}
            {/* GYM-101: flex-1 min-h-0 overflow-y-auto means this region expands
                to fill whatever space is left between the static top and controls
                region, and scrolls INTERNALLY when sets overflow. GYM-130: rows
                are ASC (comparison reads top-down); the just-saved row and the
                next ghost target are kept visible by the auto-scroll effects. */}
            {/* GYM-123 #6: polite live region — a newly appended set row is
                announced by screen readers without stealing focus. */}
            <section
                className="mt-5 min-h-0 flex-1 overflow-y-auto"
                aria-live="polite"
            >
                {!hasGhost ? (
                    <div className="shrink-0 text-label uppercase tracking-wide text-hint">
                        {t("logger.today")}
                    </div>
                ) : null}
                {recap.length === 0 ? (
                    <p className="mt-2 text-base text-hint">
                        {t("logger.noSetsYet")}
                    </p>
                ) : (
                    <ComparisonRecap
                        rows={recap}
                        hasGhost={hasGhost}
                        flareSet={flareSet}
                        justSavedSet={lastSavedSet}
                        registerRow={registerRow}
                    />
                )}
            </section>

            {/* ── Controls region: always visible, never scrolled off-screen ─── */}
            {/* GYM-101: shrink-0 keeps this region pinned at the bottom of the
                flex column regardless of how tall the recap grows. The PR chip
                lives here so it is always visible on reopen. */}
            <div className="shrink-0 pb-2">
                {/* SET heading + GYM-135 trend group + PR target chip (§12.3).
                    Placed in the fixed controls region (GYM-101) so the PR is
                    always visible regardless of how many sets are in the recap.
                    Row extracted to SetHeadingRow.tsx (file-size split). */}
                <SetHeadingRow
                    nextSet={nextSet}
                    effectivePR={effectivePR}
                    pulse={pulse}
                    muscleName={muscleName}
                    exerciseName={exerciseName}
                />

                {ctx.isLoading ? (
                    <p className="mt-2 text-label text-hint">
                        {t("logger.loadingNumbers")}
                    </p>
                ) : null}

                {/* Two pre-filled steppers (§12.3). */}
                <div className="mt-4 flex flex-col gap-6">
                    <Stepper
                        label={t("label.weight")}
                        unit={t("unit.kg")}
                        {...form.weightProps}
                    />
                    <Stepper label={t("label.reps")} {...form.repsProps} />
                </div>

                {/* Write error (§12.5) — sheet stays open, no recap was appended.
                    GYM-125 #2: a 409 (set-number collision, §12.8) gets a specific
                    message via saveErrorMessage; the onSettled invalidation in
                    useCreateTraining refetches log-context, so nextSet auto-corrects.
                    create.variables carries the body of the LAST attempt — the set
                    number the failed save actually tried to write. */}
                {create.isError ? (
                    <p className="mt-3 text-label text-accent">
                        {saveErrorMessage(
                            create.error,
                            create.variables?.set ?? nextSet,
                        )}
                    </p>
                ) : null}

                {/* Sticky in-sheet SAVE (§11.4). GYM-131 #3: while `morph` is
                    live the button shows check + "Saved set n — w×r", then
                    snaps back to "Save set {n+1}". Interactive throughout —
                    a rapid double-save restarts the morph cleanly. */}
                <SheetSaveButton
                    label={t("logger.saveSet", { n: nextSet })}
                    onClick={save}
                    disabled={!canSave}
                    pulse={pulse}
                    success={
                        morph
                            ? {
                                  label: t("logger.savedSet", {
                                      n: morph.set,
                                      weight: morph.weight,
                                      reps: morph.reps,
                                  }),
                                  nonce: morph.nonce,
                              }
                            : null
                    }
                />

                {/* Quiet "finish" affordance (§12.3). GYM-123 #7: a light
                    impact haptic marks the close. GYM-132: onDone now goes to
                    RecordSheet's handleDone — with ≥1 set logged this session
                    it body-swaps to the summary; otherwise it closes. */}
                <button
                    type="button"
                    onClick={() => {
                        hapticImpact("light");
                        onDone();
                    }}
                    className="press-95 mt-2 min-h-[44px] w-full text-base text-hint"
                >
                    {t("common.done")}
                </button>
            </div>
        </div>
    );
}
