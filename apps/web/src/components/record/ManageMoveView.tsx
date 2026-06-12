/**
 * The "Move to another muscle" view of the manage sheet (GYM-90, extracted
 * from ManageSheet.tsx in GYM-127 — file-size split, behavior identical).
 *
 * Lists every visible muscle except the exercise's current one; picking a
 * target fires the move (PATCH /exercises/{id}/muscle via the parent). While
 * one row's move is in-flight only THAT row shows "Moving…" (GYM-98); all
 * rows stay disabled. Errors render above the list and the user can retry.
 */
import type { Muscle } from "@/api/analytics";
import { useT } from "@/i18n/catalog";

interface ManageMoveViewProps {
    /** Visible muscle catalog (the parent's useMuscles data). */
    muscles: Muscle[];
    musclesLoading: boolean;
    /** The exercise's current muscle id — excluded from the target list. */
    excludeMuscleId?: number;
    moveError: string | null;
    /** The muscle row whose move mutation is in-flight (null = none, GYM-98). */
    movingMuscleId: number | null;
    /** True while ANY move mutation is in-flight (disables every row). */
    movePending: boolean;
    onBack: () => void;
    onMove: (muscleId: number, muscleName: string) => void;
}

export function ManageMoveView({
    muscles,
    musclesLoading,
    excludeMuscleId,
    moveError,
    movingMuscleId,
    movePending,
    onBack,
    onMove,
}: ManageMoveViewProps) {
    const { t, muscle } = useT();
    const targets = muscles.filter((m) => m.id !== excludeMuscleId);

    return (
        <div className="space-y-3">
            <button
                type="button"
                onClick={onBack}
                className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
            >
                ← {t("common.back")}
            </button>
            <p className="text-label uppercase tracking-wide text-hint">
                {t("move.title")}
            </p>
            {moveError ? (
                <p className="text-label text-accent">{moveError}</p>
            ) : null}
            <div className="rounded-lg border border-hairline overflow-hidden">
                {targets.map((m, idx, arr) => {
                    const isThisRowMoving = movingMuscleId === m.id;
                    return (
                        <div key={m.id}>
                            <button
                                type="button"
                                onClick={() => onMove(m.id, m.name)}
                                disabled={movePending}
                                className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text disabled:opacity-40"
                            >
                                {isThisRowMoving ? t("move.moving") : muscle(m.name)}
                            </button>
                            {idx < arr.length - 1 && (
                                <div className="h-px bg-hairline" aria-hidden />
                            )}
                        </div>
                    );
                })}
                {musclesLoading && (
                    <div className="flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-base text-hint">
                        {t("common.loading")}
                    </div>
                )}
                {!musclesLoading && targets.length === 0 && (
                    <div className="flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-base text-hint">
                        {t("manage.noOtherMuscles")}
                    </div>
                )}
            </div>
        </div>
    );
}
