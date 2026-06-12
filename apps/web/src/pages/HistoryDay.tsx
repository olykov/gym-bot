/**
 * History day-detail route (spec §11.3) — `GET /training/day/{date}`, exercises
 * grouped as <Card>s with a <SetRow> per set; tap a row → set-editor sheet,
 * swipe-left → delete (routed through the in-sheet confirm).
 *
 * BackButton ownership (§11.7): on this route (sheet closed) the Telegram Back
 * returns to the list; while the sheet is open the sheet owns Back (it closes
 * the sheet first — handled inside <BottomSheet>). When the last set of the day
 * is deleted the optimistic update empties the day → we navigate(-1) back.
 *
 * States are first-class (§11.6): a layout-matching skeleton while loading, an
 * EmptyState for an empty day / 404, an inline ErrorState + retry on error.
 */
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useT } from "@/i18n/catalog";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import type { TrainingDayDetail, TrainingSet } from "@/api/training";
import { pushBackHandler } from "@/telegram/webapp";
import { dayKey, useTrainingDay } from "@/hooks/useTraining";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { Divider } from "@/components/ui/Divider";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SetRow } from "@/components/ui/SetRow";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { SetEditor, type EditorTarget } from "@/components/history/SetEditor";
import { AddSetInline } from "@/components/history/AddSetInline";
import { useTransitionNavigate } from "@/components/shell/useTransitionNavigate";

export function HistoryDay() {
    const { t, muscle } = useT();
    const { date = "" } = useParams();
    // GYM-121: leaving the day is a pop — content slides right; unsupported
    // WebViews / reduced motion degrade to the previous instant navigate(-1).
    const transitionNavigate = useTransitionNavigate();
    const qc = useQueryClient();

    const day = useTrainingDay(date);
    const [target, setTarget] = useState<EditorTarget | null>(null);

    // GYM-52: inline error message surfaced after an optimistic rollback so the
    // user understands why the value reverted (spec §11.4/§11.7). Auto-dismissed
    // after 3 s; no jarring animation — transition respects prefers-reduced-motion.
    const [mutationError, setMutationError] = useState<string | null>(null);
    const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    function showMutationError(msg: string): void {
        if (dismissTimer.current) clearTimeout(dismissTimer.current);
        setMutationError(msg);
        dismissTimer.current = setTimeout(() => setMutationError(null), 3000);
    }

    // Clean up the timer on unmount.
    useEffect(() => () => {
        if (dismissTimer.current) clearTimeout(dismissTimer.current);
    }, []);

    // BackButton: on this route, Back returns to the list (the sheet, while open,
    // overrides this — see <BottomSheet>). GYM-119: pushed onto the shared
    // back-handler stack so visibility has a single owner; the sheet's own
    // handler stacks above this one while open. Pushed only when the sheet is
    // closed (the early return keeps the route layer off the stack meanwhile).
    useEffect(() => {
        if (target) return; // sheet owns Back while open
        return pushBackHandler(() => transitionNavigate(-1, "back"));
    }, [transitionNavigate, target]);

    function openEditor(
        set: TrainingSet,
        exerciseName: string,
        muscleName: string,
    ): void {
        setTarget({ set, exerciseName, muscleName });
    }

    function closeEditor(): void {
        setTarget(null);
    }

    // After a delete, if the optimistic update emptied the day, go back (§11.3).
    // Read the LIVE cache (the onMutate patch already applied) — not the stale
    // hook closure, which hasn't re-rendered yet.
    function afterDelete(): void {
        const detail = qc.getQueryData<TrainingDayDetail>(dayKey(date));
        const remaining = detail?.exercises.some((e) => e.sets.length > 0);
        if (detail && !remaining) transitionNavigate(-1, "back");
    }

    if (day.isLoading) return <DayDetailSkeleton />;

    if (day.isError) {
        const notFound =
            day.error instanceof ApiError && day.error.status === 404;
        if (notFound) {
            return (
                <EmptyState
                    title={t("empty.dayTitle")}
                    subtitle={t("empty.dayNotFound")}
                />
            );
        }
        return <ErrorState onRetry={() => day.refetch()} />;
    }

    const detail = day.data;
    const exercises = (detail?.exercises ?? []).filter(
        (e) => e.sets.length > 0,
    );

    if (exercises.length === 0) {
        return (
            <EmptyState
                title={t("empty.dayTitle")}
                subtitle={t("empty.dayNoSets")}
            />
        );
    }

    return (
        <>
            {/* GYM-52: mutation-error banner — surfaces after an optimistic rollback
                so the user understands why the value reverted. Token-only styling
                (text-label + text-accent matches the existing write-error pattern in
                SetLogger §12.5). Auto-dismissed after 3 s; transition is guarded by
                motion-reduce so it never causes discomfort. */}
            {mutationError ? (
                <div
                    aria-live="polite"
                    className="mb-3 rounded-md border border-hairline bg-secondary-bg px-3 py-2 transition-opacity duration-300 motion-reduce:transition-none"
                >
                    <p className="text-label text-accent">{mutationError}</p>
                </div>
            ) : null}

            {exercises.map((ex) => (
                <Card key={ex.exercise_id}>
                    {/* GYM-77 #2: exercise name clips with ellipsis; muscle chip
                        has a shrink-0 + max-width wrapper so it never overflows. */}
                    <div className="mb-3 flex items-center gap-3">
                        <h2 className="min-w-0 flex-1 truncate text-base font-semibold text-text" title={ex.exercise_name}>
                            {ex.exercise_name}
                        </h2>
                        <span className="min-w-0 max-w-chip shrink-0">
                            <Chip title={muscle(ex.muscle_name)}>
                                {muscle(ex.muscle_name)}
                            </Chip>
                        </span>
                    </div>

                    {ex.sets.map((set, i) => (
                        <div key={set.training_id}>
                            {i > 0 ? <Divider /> : null}
                            <SetRow
                                set={set}
                                onEdit={() =>
                                    openEditor(
                                        set,
                                        ex.exercise_name,
                                        ex.muscle_name,
                                    )
                                }
                                onDelete={() =>
                                    openEditor(
                                        set,
                                        ex.exercise_name,
                                        ex.muscle_name,
                                    )
                                }
                            />
                        </div>
                    ))}

                    {/* GYM-51: add-set retroactively for this exercise on this day. */}
                    <Divider />
                    <AddSetInline
                        date={date}
                        muscleName={ex.muscle_name}
                        exerciseName={ex.exercise_name}
                        existingSets={ex.sets}
                    />
                </Card>
            ))}

            {/* GYM-143: fixedHeight=true so the panel has a bounded, fixed
               height (clears both AppShell header and BottomNav). SetEditor
               fills the body via flex-col flex-1 min-h-0 — the flex-column
               model eliminates both the REPS-behind-SAVE overlap and the
               dead-space-below-SAVE issue without any sticky/padding tricks. */}
            <BottomSheet
                open={target !== null}
                onClose={closeEditor}
                titleId="set-editor-title"
                fixedHeight
            >
                {target ? (
                    <SetEditor
                        date={date}
                        target={target}
                        titleId="set-editor-title"
                        onClose={closeEditor}
                        onDeleted={afterDelete}
                        onEditError={() =>
                            showMutationError(t("history.saveRestored"))
                        }
                        onDeleteError={() =>
                            showMutationError(t("history.deleteRestored"))
                        }
                    />
                ) : null}
            </BottomSheet>
        </>
    );
}

/** Exercise-group skeleton with set-row bars (matches the loaded layout). */
function DayDetailSkeleton() {
    return (
        <>
            {Array.from({ length: 2 }).map((_, c) => (
                <Card key={c}>
                    <div className="mb-3 flex items-center justify-between">
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-6 w-16 rounded-full" />
                    </div>
                    {Array.from({ length: 3 }).map((__, r) => (
                        <Skeleton key={r} className="my-2 h-6 w-full" />
                    ))}
                </Card>
            ))}
        </>
    );
}
