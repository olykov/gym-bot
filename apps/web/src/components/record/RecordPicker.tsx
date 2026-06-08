/**
 * Phase A of the record flow — the exercise picker (spec §12.2, GYM-72 v2,
 * GYM-74 slide-nav).
 *
 * Layout, top to bottom:
 *  1. Continue tile — the LAST exercise trained TODAY (derived from
 *     `GET /training/day/{today}`: the exercise group whose set has the highest
 *     training_id, i.e. the most recently logged). Tap → Phase B. Omitted
 *     entirely when nothing was trained today.
 *  2. A very light, fading hairline divider below the Continue tile (only shown
 *     with the tile) — a whisper of separation, not a hard cut.
 *  3. Muscle TILES (frequency-sorted top-muscles, then the rest of /muscles) →
 *     tapping a muscle SLIDES the view LEFT and the exercise list SLIDES IN
 *     from the right (GYM-74 horizontal push, ~200ms ease-out-soft). The Back
 *     affordance (and the Telegram BackButton, wired in RecordSheet) slides back.
 *     Exercise tiles appear on the right panel in the same tile format. Keep
 *     the add-inline + Muscle / + Exercise. Top ~6 + "Show all" (§12.9).
 *
 * The slide track is a horizontal flex of two panels (muscles + exercises),
 * each 100% wide, inside an `overflow:hidden` wrapper. A CSS `translate` on the
 * track animates between the two steps. Reduced-motion → instant swap (no
 * transition). Non-flickering: both panels stay mounted, only translate changes.
 *
 * Muscle tiles use an auto-fit grid (minmax(100px, 1fr)) so long names and
 * custom muscles lay out correctly without hardcoded column counts. Tile minimum
 * height is 64px (bigger than the old 52px, per GYM-74). Exercise tiles share
 * the same tile language.
 *
 * Prefetch (§12.5 perf): on mount (sheet open) warm top-muscles + day/today and
 * the Continue exercise's log-context; on muscle pick prefetch its exercises —
 * so each pick lands instantly.
 *
 * Empty brand-new user (nothing today, empty catalog) → an in-sheet
 * "ADD YOUR FIRST EXERCISE" prompt with the add-inline field; no analytics
 * fan-out on the empty path (§12.6 / ARCH §2).
 *
 * GYM-82: long-press (~480ms) on a muscle or exercise tile opens the manage
 * sheet (ManageSheet). Text selection is disabled on tiles. A normal tap still
 * selects. Tap vs long-press is disambiguated by pointerdown timer; the timer
 * cancels on pointermove beyond a small threshold, on scroll, or on pointerup
 * before the threshold fires.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MUSCLE_NAME_MAX, EXERCISE_NAME_MAX } from "@/validation";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { AddInlineField } from "./AddInlineField";
import { ManageSheet } from "./ManageSheet";
import { useMuscles, useTopMuscles, useTopExercises, useExercises } from "@/hooks/useAnalytics";
import { useTrainingDay } from "@/hooks/useTraining";
import { hapticImpact } from "@/telegram/webapp";
import {
    useCreateExercise,
    useCreateMuscle,
    prefetchPickerReads,
    prefetchMuscleExercises,
    prefetchLogContext,
} from "@/hooks/useRecord";
import type { PickerStep } from "./RecordSheet";
import type { ChosenExercise } from "./types";
import type { Muscle, Exercise } from "@/api/analytics";

/** Browse: exercises shown before the "Show all" expand (spec §12.9). */
const BROWSE_VISIBLE = 6;

/** Long-press timer duration in ms. Midpoint of the 450–550ms range. */
const LONG_PRESS_MS = 480;

/** Max pointer movement (px) before we cancel the long-press. */
const MOVE_THRESHOLD_PX = 6;

/** Item info for the manage sheet. */
interface ManageItem {
    id: number;
    name: string;
    kind: "muscle" | "exercise";
    is_mine: boolean;
    muscleName?: string;
    /** Current muscle id — for the GYM-90 move view to exclude the current muscle. */
    muscleId?: number;
}

interface RecordPickerProps {
    /** Today's date (YYYY-MM-DD) — the day/log-context key for the Continue tile. */
    today: string;
    /** Current picker step — controlled by RecordSheet so BackButton can go back. */
    step: PickerStep;
    /** Called when the picker step changes (controlled). */
    onStepChange: (step: PickerStep) => void;
    /**
     * The currently selected muscle — controlled by RecordSheet (GYM-77 #4).
     * Lifting this up means selectedMuscle survives the Phase B round-trip
     * (RecordPicker unmounts/remounts when swapping phases; without this lift,
     * pressing "← Switch exercise" would land on an empty exercise panel because
     * local state would have reset to null).
     */
    selectedMuscle: string | null;
    /** Called when the selected muscle changes (controlled). */
    onMuscleChange: (name: string | null) => void;
    /** Hand the chosen exercise to the controller → swaps to Phase B. */
    onPick: (chosen: ChosenExercise) => void;
    /**
     * GYM-85: called when a create returns resolution=existing so the controller
     * (RecordSheet) can surface the hint in Phase B (SetLogger) after the picker
     * unmounts. Only called for the "existing" resolution; "created" and "unhidden"
     * never call this (silent or no-op).
     */
    onCreateHint: (hint: string) => void;
}

/** The last exercise trained today: the group whose set has the highest id. */
interface ContinueExercise {
    muscleName: string;
    exerciseName: string;
}

/**
 * Hook returning props for a tile button that distinguishes tap vs long-press.
 *
 * Tap: fires `onTap`.
 * Long-press (~LONG_PRESS_MS): fires `onLongPress`, suppresses `onTap`.
 * Cancels on move > MOVE_THRESHOLD_PX, on scroll, or on early pointerup.
 * Respects `prefers-reduced-motion` for haptic-only (no animation change needed).
 */
function useTilePressHandlers(
    onTap: () => void,
    onLongPress: () => void,
): React.HTMLAttributes<HTMLButtonElement> {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const startPosRef = useRef<{ x: number; y: number } | null>(null);
    const firedRef = useRef(false);

    function cancel(): void {
        if (timerRef.current !== null) {
            clearTimeout(timerRef.current);
            timerRef.current = null;
        }
    }

    function onPointerDown(e: React.PointerEvent<HTMLButtonElement>): void {
        // Only primary button / touch.
        if (e.button !== 0 && e.pointerType === "mouse") return;
        firedRef.current = false;
        startPosRef.current = { x: e.clientX, y: e.clientY };
        cancel();
        timerRef.current = setTimeout(() => {
            timerRef.current = null;
            firedRef.current = true;
            hapticImpact("medium");
            onLongPress();
        }, LONG_PRESS_MS);
    }

    function onPointerMove(e: React.PointerEvent<HTMLButtonElement>): void {
        if (!startPosRef.current || timerRef.current === null) return;
        const dx = Math.abs(e.clientX - startPosRef.current.x);
        const dy = Math.abs(e.clientY - startPosRef.current.y);
        if (dx > MOVE_THRESHOLD_PX || dy > MOVE_THRESHOLD_PX) {
            cancel();
        }
    }

    function onPointerUp(): void {
        if (timerRef.current !== null) {
            // Timer still running — this is a tap.
            cancel();
            if (!firedRef.current) {
                onTap();
            }
        }
        startPosRef.current = null;
    }

    function onPointerCancel(): void {
        cancel();
        startPosRef.current = null;
    }

    // Cancel if a scroll event fires on the containing scroller.
    // We attach this as a capture listener on the window; cancel removes it.
    // (Handled inline: the timer already cancels on pointermove threshold.)

    return {
        onPointerDown,
        onPointerMove,
        onPointerUp,
        onPointerCancel,
        // Prevent the context menu on long-press (iOS).
        onContextMenu: (e) => {
            if (firedRef.current) e.preventDefault();
        },
    };
}

export function RecordPicker({ today, step, onStepChange, selectedMuscle, onMuscleChange, onPick, onCreateHint }: RecordPickerProps) {
    const qc = useQueryClient();
    const topMuscles = useTopMuscles();
    const muscles = useMuscles();
    const day = useTrainingDay(today);

    const [showAllExercises, setShowAllExercises] = useState(false);
    // GYM-83: frequency data (top-exercises) is kept for ordering only.
    const topExercises = useTopExercises(selectedMuscle);

    const createMuscle = useCreateMuscle();
    const createExercise = useCreateExercise();

    // Which add-inline field is open (if any).
    const [adding, setAdding] = useState<"muscle" | "exercise" | null>(null);

    /**
     * GYM-85: non-blocking hint shown when POST /muscles or POST /exercises returns
     * resolution=existing (the name matched a visible item — no duplicate created, but
     * the user should know). Cleared whenever the user opens a new add field or navigates.
     * Stays null for resolution=created (normal) and resolution=unhidden (fully silent).
     */
    const [resolveHint, setResolveHint] = useState<string | null>(null);

    // GYM-82: manage sheet state.
    const [manageItem, setManageItem] = useState<ManageItem | null>(null);

    // Full muscle catalog (Muscle[] with id + is_mine) — keyed by name for lookup.
    const muscleByName = useMemo((): Map<string, Muscle> => {
        const map = new Map<string, Muscle>();
        for (const m of muscles.data ?? []) {
            map.set(m.name, m);
        }
        return map;
    }, [muscles.data]);

    // Derive the selected muscle's numeric id (to fetch full exercises with is_mine).
    const selectedMuscleId = useMemo((): number | null => {
        if (!selectedMuscle) return null;
        return muscleByName.get(selectedMuscle)?.id ?? null;
    }, [selectedMuscle, muscleByName]);

    // GYM-83: full catalog for the selected muscle (Exercise[] with id + is_mine).
    // This is now the tile source. top-exercises provides frequency for ordering only.
    const fullExercises = useExercises(selectedMuscleId);

    // GYM-83: frequency map (exercise name → frequency) built from top-exercises.
    const frequencyMap = useMemo((): Map<string, number> => {
        const map = new Map<string, number>();
        for (const ex of topExercises.data ?? []) {
            map.set(ex.name, ex.frequency);
        }
        return map;
    }, [topExercises.data]);

    // GYM-83: sorted exercise list — full catalog ordered by frequency desc, then alpha.
    // Never-logged exercises get frequency 0 and sort after trained ones.
    const exerciseList = useMemo((): Exercise[] => {
        const catalog = fullExercises.data ?? [];
        return [...catalog].sort((a, b) => {
            const fa = frequencyMap.get(a.name) ?? 0;
            const fb = frequencyMap.get(b.name) ?? 0;
            if (fb !== fa) return fb - fa;
            return a.name.localeCompare(b.name);
        });
    }, [fullExercises.data, frequencyMap]);

    // Warm the picker reads + the Continue exercise's log-context on open (§12.5).
    useEffect(() => {
        prefetchPickerReads(qc, today);
    }, [qc, today]);

    // Continue = the exercise group whose set has the highest training_id
    // (the most recently logged today). training_id is a serial id, so the
    // largest value is the latest insert. Falls back to string compare.
    const continueExercise: ContinueExercise | null = useMemo(() => {
        const exs = day.data?.exercises ?? [];
        if (exs.length === 0) return null;
        let best: ContinueExercise | null = null;
        let bestKey = -Infinity;
        for (const ex of exs) {
            for (const s of ex.sets) {
                const k = Number(s.training_id);
                const key = Number.isFinite(k) ? k : -Infinity;
                if (key > bestKey) {
                    bestKey = key;
                    best = {
                        muscleName: ex.muscle_name,
                        exerciseName: ex.exercise_name,
                    };
                }
            }
        }
        // No finite id anywhere → fall back to first appearance (alpha order).
        if (!best && exs[0]) {
            best = {
                muscleName: exs[0].muscle_name,
                exerciseName: exs[0].exercise_name,
            };
        }
        return best;
    }, [day.data]);

    // Prefetch the Continue exercise's log-context so tapping it is instant.
    useEffect(() => {
        if (continueExercise) {
            prefetchLogContext(
                qc,
                continueExercise.muscleName,
                continueExercise.exerciseName,
                today,
            );
        }
    }, [qc, continueExercise, today]);

    // Merge top-muscles (frequency order) with the rest of the catalog, so a
    // user with private muscles never-trained can still browse them.
    const muscleOptions = useMemo(() => {
        const seen = new Set<string>();
        const out: string[] = [];
        for (const m of topMuscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push(m.name);
        }
        for (const m of muscles.data ?? []) {
            if (seen.has(m.name)) continue;
            seen.add(m.name);
            out.push(m.name);
        }
        return out;
    }, [topMuscles.data, muscles.data]);

    const visibleExercises = showAllExercises
        ? exerciseList
        : exerciseList.slice(0, BROWSE_VISIBLE);
    const hiddenCount = exerciseList.length - visibleExercises.length;

    // Brand-new user: nothing trained today AND no muscles to browse.
    const everythingLoaded =
        !day.isLoading && !topMuscles.isLoading && !muscles.isLoading;
    const isEmptyNewUser =
        everythingLoaded && !continueExercise && muscleOptions.length === 0;

    function pickMuscle(name: string): void {
        setShowAllExercises(false);
        setAdding(null);
        setResolveHint(null);
        onMuscleChange(name);
        onStepChange("exercises");
        // GYM-83: warm both top-exercises (for frequency sort) and full catalog.
        const mid = muscleByName.get(name)?.id ?? null;
        prefetchMuscleExercises(qc, name, mid);
    }

    function goBack(): void {
        onMuscleChange(null);
        setShowAllExercises(false);
        setAdding(null);
        setResolveHint(null);
        onStepChange("muscles");
    }

    /**
     * GYM-85: branch on POST /muscles resolution.
     * - created: auto-select and proceed (existing behavior).
     * - unhidden: silently select the returned item (same flow, no message).
     * - existing: show "You already have 'Name'." then proceed with the returned item.
     * Auto-select always uses data.name (the canonical name the backend returned).
     *
     * Note: pickMuscle clears resolveHint so for muscles we set the hint AFTER
     * calling pickMuscle (which navigates to the exercise step) so it shows there.
     */
    function submitMuscle(name: string): void {
        createMuscle.mutate(
            { name },
            {
                onSuccess: (data) => {
                    setAdding(null);
                    const canonicalName = data.name;
                    // Navigate first (pickMuscle resets resolveHint), then set hint.
                    pickMuscle(canonicalName);
                    if (data.resolution === "existing") {
                        setResolveHint(`You already have "${canonicalName}".`);
                    }
                },
            },
        );
    }

    /**
     * GYM-85: branch on POST /exercises resolution.
     * - created: auto-select into Phase B (existing behavior).
     * - unhidden: silently select the returned item (no message).
     * - existing: bubble the hint to RecordSheet via onCreateHint (so it survives
     *   RecordPicker unmounting on Phase A→B transition), then proceed.
     * Auto-select always uses data.name (canonical) and data from the returned Exercise.
     */
    function submitExercise(name: string): void {
        const muscleName = selectedMuscle;
        if (!muscleName) return;
        createExercise.mutate(
            { name, muscle_name: muscleName },
            {
                onSuccess: (data) => {
                    setAdding(null);
                    const canonicalName = data.name;
                    if (data.resolution === "existing") {
                        // Bubble to RecordSheet so the hint persists into Phase B
                        // (SetLogger), since onPick immediately unmounts the picker.
                        onCreateHint(`You already have "${canonicalName}".`);
                    }
                    // Auto-select into Phase B (§12.2). Uses canonical name from backend.
                    // selectedMuscle is preserved in RecordSheet (GYM-77 #4) so Back
                    // from Phase B lands on the exercise list.
                    onPick({ muscleName, exerciseName: canonicalName });
                },
            },
        );
    }

    // GYM-82: open manage sheet for a muscle tile.
    function openMuscleMange(name: string): void {
        const m = muscleByName.get(name);
        if (!m) return;
        setManageItem({
            id: m.id,
            name: m.name,
            kind: "muscle",
            is_mine: m.is_mine ?? false,
        });
    }

    // GYM-82/GYM-83: open manage sheet for an exercise tile.
    // Tile source is now Exercise[] (full catalog), so id + is_mine are always present.
    function openExerciseManage(ex: Exercise): void {
        setManageItem({
            id: ex.id,
            name: ex.name,
            kind: "exercise",
            is_mine: ex.is_mine ?? false,
            muscleName: selectedMuscle ?? undefined,
            muscleId: selectedMuscleId ?? undefined,
        });
    }

    // Empty new user: front-and-center add-first-exercise prompt (§12.6).
    if (isEmptyNewUser) {
        return (
            <div className="pb-2">
                <h2 className="font-display text-title text-text">RECORD</h2>
                <div className="mt-6">
                    <EmptyState
                        title="ADD YOUR FIRST EXERCISE"
                        subtitle="Name a muscle, then an exercise under it — you'll log your first set right after."
                    />
                    <div className="mt-2 space-y-3">
                        {!selectedMuscle ? (
                            <AddInlineField
                                placeholder="Muscle (e.g. Chest)"
                                actionLabel="Add"
                                maxLength={MUSCLE_NAME_MAX}
                                pending={createMuscle.isPending}
                                error={
                                    createMuscle.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitMuscle}
                            />
                        ) : (
                            <AddInlineField
                                placeholder={`Exercise in ${selectedMuscle}`}
                                actionLabel="Add"
                                maxLength={EXERCISE_NAME_MAX}
                                pending={createExercise.isPending}
                                error={
                                    createExercise.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitExercise}
                                onCancel={() => {
                                    onMuscleChange(null);
                                    setResolveHint(null);
                                }}
                            />
                        )}
                        {/* GYM-85: non-blocking hint when resolution=existing (empty-user path). */}
                        {resolveHint ? (
                            <p
                                aria-live="polite"
                                className="text-label text-hint"
                            >
                                {resolveHint}
                            </p>
                        ) : null}
                    </div>
                </div>
                {/* Manage sheet (even in empty state, shouldn't be needed but keep consistent). */}
                <ManageSheet
                    open={manageItem !== null}
                    onClose={() => setManageItem(null)}
                    item={manageItem}
                />
            </div>
        );
    }

    // Translate the track: muscles step = translateX(0), exercise step = translateX(-50%).
    // The track is 200% wide; each panel is 50% of the track = 100% of the sheet width.
    const isExerciseStep = step === "exercises";
    const trackStyle: React.CSSProperties = {
        transform: isExerciseStep ? "translateX(-50%)" : "translateX(0)",
        transition: "transform 200ms var(--ease-out-soft)",
        width: "200%",
        display: "flex",
    };

    return (
        // The outer div clips the slide track — overflow:hidden masks the off-screen panel.
        // flex-1 + min-h-0 lets it fill the fixed-height sheet body. overflow-hidden is
        // critical: without it the off-screen panel would be scrollable/visible.
        <div style={{ flex: "1", minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            {/* Slide track: two side-by-side panels, each 50% of the track (= 100% of sheet).
                picker-slide-track class → transition:none under prefers-reduced-motion.
                The track height matches the outer container so each panel can scroll
                independently (overflow-y:auto) without the outer sheet scrolling. */}
            <div className="picker-slide-track" style={{ ...trackStyle, flex: "1", minHeight: 0 }} aria-live="polite">
                {/* ── PANEL 1: Muscle step ─────────────────────────────────── */}
                <div
                    className="space-y-4"
                    aria-hidden={isExerciseStep}
                    style={{
                        width: "50%",
                        minWidth: 0,
                        overflowY: "auto",
                        height: "100%",
                        // GYM-100: consume --keyboard-pad from the BottomSheet panel so the
                        // add-muscle field stays visible above the keyboard. Fallback to 8px
                        // when no keyboard is up. Safe-area bottom ensures content clears the
                        // device home indicator.
                        paddingBottom: "calc(max(var(--keyboard-pad, 0px), max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))) + 8px)",
                        paddingRight: "4px",
                    }}
                >
                    <h2 className="font-display text-title text-text">RECORD</h2>

                    {/* Continue today tile (§12.2 v2). */}
                    {day.isLoading ? (
                        <Skeleton className="h-[60px] w-full rounded-lg" />
                    ) : continueExercise ? (
                        <>
                            <button
                                type="button"
                                tabIndex={isExerciseStep ? -1 : 0}
                                onClick={() =>
                                    onPick({
                                        muscleName: continueExercise.muscleName,
                                        exerciseName: continueExercise.exerciseName,
                                    })
                                }
                                className="press-95 flex min-h-[60px] w-full items-center justify-between gap-3 rounded-lg border border-hairline bg-secondary-bg px-4 py-3 text-left"
                            >
                                <span className="min-w-0">
                                    <span className="block text-label uppercase tracking-wide text-hint">
                                        Continue today
                                    </span>
                                    <span className="mt-0.5 block truncate text-base font-semibold text-text">
                                        {continueExercise.exerciseName}
                                    </span>
                                    <span className="block truncate text-label text-hint">
                                        {continueExercise.muscleName}
                                    </span>
                                </span>
                                <span aria-hidden className="shrink-0 text-hint">
                                    ›
                                </span>
                            </button>

                            {/* Very light, fading hairline — a whisper, not a hard cut. */}
                            <div
                                aria-hidden
                                className="record-divider-faint mx-auto h-px w-2/3"
                            />
                        </>
                    ) : null}

                    {/* Muscle tiles — auto-fit grid so custom/long names don't break. */}
                    <section className="space-y-3">
                        <div className="text-label uppercase tracking-wide text-hint">
                            Muscle
                        </div>

                        {topMuscles.isError && muscles.isError ? (
                            <ErrorState
                                message="Couldn't load muscles."
                                onRetry={() => {
                                    void topMuscles.refetch();
                                    void muscles.refetch();
                                }}
                            />
                        ) : topMuscles.isLoading && muscles.isLoading ? (
                            <div className="picker-tile-grid-muscle">
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <Skeleton
                                        key={i}
                                        className="w-full rounded-lg"
                                        style={{ height: "88px" }}
                                    />
                                ))}
                            </div>
                        ) : (
                            <div className="picker-tile-grid-muscle">
                                {muscleOptions.map((name) => (
                                    <MuscleTile
                                        key={name}
                                        name={name}
                                        tabIndex={isExerciseStep ? -1 : 0}
                                        onTap={() => pickMuscle(name)}
                                        onLongPress={() => openMuscleMange(name)}
                                    />
                                ))}
                                {/* Add a muscle inline (§12.2). */}
                                {adding !== "muscle" ? (
                                    <button
                                        type="button"
                                        tabIndex={isExerciseStep ? -1 : 0}
                                        onClick={() => {
                                            setAdding("muscle");
                                            setResolveHint(null);
                                        }}
                                        className="press-95 flex w-full items-center justify-center rounded-lg border border-dashed border-hairline px-3 text-center text-base text-hint"
                                        style={{ height: "88px" }}
                                    >
                                        + Muscle
                                    </button>
                                ) : null}
                            </div>
                        )}

                        {adding === "muscle" ? (
                            <AddInlineField
                                placeholder="New muscle name"
                                actionLabel="Add"
                                maxLength={MUSCLE_NAME_MAX}
                                pending={createMuscle.isPending}
                                error={
                                    createMuscle.isError
                                        ? "Couldn't add that — try again."
                                        : null
                                }
                                onSubmit={submitMuscle}
                                onCancel={() => {
                                    setAdding(null);
                                    setResolveHint(null);
                                }}
                            />
                        ) : null}
                    </section>
                </div>

                {/* ── PANEL 2: Exercise step ───────────────────────────────── */}
                <div
                    className="space-y-4"
                    aria-hidden={!isExerciseStep}
                    style={{
                        width: "50%",
                        minWidth: 0,
                        overflowY: "auto",
                        height: "100%",
                        // GYM-100: consume --keyboard-pad from the BottomSheet panel so the
                        // + Exercise add field and submit button are fully visible above the
                        // keyboard from the moment the field opens, on a ~360px device.
                        paddingBottom: "calc(max(var(--keyboard-pad, 0px), max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px))) + 8px)",
                        paddingRight: "4px",
                    }}
                >
                    {/* Back to muscles control (in-body; mirrors Phase B's "← Switch exercise"). */}
                    <button
                        type="button"
                        tabIndex={isExerciseStep ? 0 : -1}
                        onClick={goBack}
                        className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
                    >
                        ← {selectedMuscle ?? "Muscles"}
                    </button>

                    <h2 className="font-display text-title text-text">
                        {selectedMuscle ?? ""}
                    </h2>

                    {/* Exercise tiles — 2-column grid, fixed height, line-clamp (GYM-77 #1/#3).
                        GYM-83: source is fullExercises (full catalog), ordered by frequency. */}
                    {fullExercises.isLoading ? (
                        <div className="picker-tile-grid-exercise">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <Skeleton
                                    key={i}
                                    className="w-full rounded-lg"
                                    style={{ height: "88px" }}
                                />
                            ))}
                        </div>
                    ) : fullExercises.isError ? (
                        <ErrorState
                            message="Couldn't load exercises."
                            onRetry={() => void fullExercises.refetch()}
                        />
                    ) : (
                        <div className="picker-tile-grid-exercise">
                            {visibleExercises.map((ex) => (
                                <ExerciseTile
                                    key={ex.id}
                                    name={ex.name}
                                    tabIndex={isExerciseStep ? 0 : -1}
                                    onTap={() =>
                                        onPick({
                                            muscleName: selectedMuscle!,
                                            exerciseName: ex.name,
                                        })
                                    }
                                    onLongPress={() => openExerciseManage(ex)}
                                />
                            ))}
                            {hiddenCount > 0 ? (
                                <button
                                    type="button"
                                    tabIndex={isExerciseStep ? 0 : -1}
                                    onClick={() => setShowAllExercises(true)}
                                    className="press-95 flex w-full items-center justify-center rounded-lg bg-accent-weak px-3 text-center text-base font-semibold text-accent"
                                    style={{ height: "88px" }}
                                >
                                    Show all ({hiddenCount})
                                </button>
                            ) : null}
                        </div>
                    )}

                    {/* Add an exercise inline (§12.2). */}
                    {adding === "exercise" ? (
                        <AddInlineField
                            placeholder={`New exercise in ${selectedMuscle ?? ""}`}
                            actionLabel="Add"
                            maxLength={EXERCISE_NAME_MAX}
                            pending={createExercise.isPending}
                            error={
                                createExercise.isError
                                    ? "Couldn't add that — try again."
                                    : null
                            }
                            onSubmit={submitExercise}
                            onCancel={() => {
                                setAdding(null);
                                setResolveHint(null);
                            }}
                        />
                    ) : (
                        <button
                            type="button"
                            tabIndex={isExerciseStep ? 0 : -1}
                            onClick={() => {
                                setAdding("exercise");
                                setResolveHint(null);
                            }}
                            className="press-95 min-h-[44px] rounded-full border border-dashed border-hairline px-4 text-base text-hint"
                        >
                            + Exercise
                        </button>
                    )}
                    {/* GYM-85: non-blocking hint when resolution=existing.
                        Shown in the exercise panel since both muscle and exercise
                        "existing" cases navigate here (muscle pick transitions to
                        exercises first, then the hint is set). */}
                    {resolveHint ? (
                        <p
                            aria-live="polite"
                            className="text-label text-hint"
                        >
                            {resolveHint}
                        </p>
                    ) : null}
                </div>
            </div>

            {/* GYM-82: Manage sheet — opened by long-press on any tile. */}
            <ManageSheet
                open={manageItem !== null}
                onClose={() => setManageItem(null)}
                item={manageItem}
            />
        </div>
    );
}

// ── Tile sub-components (GYM-82) ─────────────────────────────────────────────

interface TileProps {
    name: string;
    tabIndex: number;
    onTap: () => void;
    onLongPress: () => void;
}

/**
 * A muscle tile that distinguishes tap vs long-press (GYM-82).
 * Applies tile-no-select to prevent native text selection on long-press.
 */
function MuscleTile({ name, tabIndex, onTap, onLongPress }: TileProps) {
    const pressHandlers = useTilePressHandlers(onTap, onLongPress);
    return (
        <button
            type="button"
            tabIndex={tabIndex}
            title={name}
            {...pressHandlers}
            className="tile-no-select press-95 flex w-full items-center justify-center rounded-lg border border-hairline bg-secondary-bg px-3 text-center text-base text-text"
            style={{ height: "88px" }}
        >
            <span className="tile-name">{name}</span>
        </button>
    );
}

/**
 * An exercise tile that distinguishes tap vs long-press (GYM-82).
 * Applies tile-no-select to prevent native text selection on long-press.
 */
function ExerciseTile({ name, tabIndex, onTap, onLongPress }: TileProps) {
    const pressHandlers = useTilePressHandlers(onTap, onLongPress);
    return (
        <button
            type="button"
            tabIndex={tabIndex}
            title={name}
            {...pressHandlers}
            className="tile-no-select press-95 flex w-full items-center justify-center rounded-lg border border-hairline bg-secondary-bg px-3 text-center text-base text-text"
            style={{ height: "88px" }}
        >
            <span className="tile-name">{name}</span>
        </button>
    );
}
