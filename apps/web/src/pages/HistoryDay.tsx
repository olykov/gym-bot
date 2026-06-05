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
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import type { TrainingDayDetail, TrainingSet } from "@/api/training";
import {
    hideBackButton,
    showBackButton,
    wireBackButton,
} from "@/telegram/webapp";
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

export function HistoryDay() {
    const { date = "" } = useParams();
    const navigate = useNavigate();
    const qc = useQueryClient();

    const day = useTrainingDay(date);
    const [target, setTarget] = useState<EditorTarget | null>(null);

    // BackButton: on this route, Back returns to the list (the sheet, while open,
    // overrides this — see <BottomSheet>). Wired only when the sheet is closed.
    useEffect(() => {
        if (target) return; // sheet owns Back while open
        showBackButton();
        const teardown = wireBackButton(() => navigate(-1));
        return () => {
            teardown();
            hideBackButton();
        };
    }, [navigate, target]);

    function openEditor(set: TrainingSet, exerciseName: string): void {
        setTarget({ set, exerciseName });
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
        if (detail && !remaining) navigate(-1);
    }

    if (day.isLoading) return <DayDetailSkeleton />;

    if (day.isError) {
        const notFound =
            day.error instanceof ApiError && day.error.status === 404;
        if (notFound) {
            return (
                <EmptyState
                    title="Empty day"
                    subtitle="This day has no trainings."
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
                title="Empty day"
                subtitle="No sets recorded on this day."
            />
        );
    }

    return (
        <>
            {exercises.map((ex) => (
                <Card key={ex.exercise_id}>
                    {/* GYM-77 #2: exercise name clips with ellipsis; muscle chip
                        has a shrink-0 + max-width wrapper so it never overflows. */}
                    <div className="mb-3 flex items-center gap-3">
                        <h2 className="min-w-0 flex-1 truncate text-base font-semibold text-text" title={ex.exercise_name}>
                            {ex.exercise_name}
                        </h2>
                        <span className="min-w-0 shrink-0" style={{ maxWidth: "8rem" }}>
                            <Chip title={ex.muscle_name}>{ex.muscle_name}</Chip>
                        </span>
                    </div>

                    {ex.sets.map((set, i) => (
                        <div key={set.training_id}>
                            {i > 0 ? <Divider /> : null}
                            <SetRow
                                set={set}
                                onEdit={() =>
                                    openEditor(set, ex.exercise_name)
                                }
                                onDelete={() =>
                                    openEditor(set, ex.exercise_name)
                                }
                            />
                        </div>
                    ))}
                </Card>
            ))}

            <BottomSheet
                open={target !== null}
                onClose={closeEditor}
                titleId="set-editor-title"
            >
                {target ? (
                    <SetEditor
                        date={date}
                        target={target}
                        titleId="set-editor-title"
                        onClose={closeEditor}
                        onDeleted={afterDelete}
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
