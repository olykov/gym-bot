/**
 * In-design manage sheet for a muscle or exercise tile (GYM-82, spec §12.2).
 *
 * Opened by a ~480ms long-press on a muscle or exercise tile. Reuses the shared
 * <BottomSheet> (auto-height, not fixedHeight) so it slides up in the same
 * Chalk & Iron language as every other sheet. The sheet is deliberately small —
 * one or two action rows + an optional confirm/rename/move sub-view — to feel like
 * a contextual menu, not a new screen.
 *
 * Ownership-gated (GYM-80 `is_mine`):
 *   - Own custom item (`is_mine === true`): Rename + Move to another muscle +
 *     Hide + Delete. GYM-100: Hide is now also available for own items —
 *     an own item with history can't be deleted (409 guard), so Hide is the only
 *     way to declutter it. The full action set: Rename / Move (exercises only) /
 *     Hide / Delete — always all four, never fewer.
 *     - Rename → inline edit reusing AddInlineField pattern, pre-filled, enforces
 *       maxLength. 409 (dup name) → graceful inline message; 422 → server message.
 *     - Move (exercises only, GYM-90) → muscle list (all visible muscles, excluding
 *       the current one). Picking a target calls PATCH /exercises/{id}/muscle.
 *       On success: close + full invalidation. 409 (name collision in target) →
 *       graceful inline message, stay in move view. 403/404 → graceful error.
 *     - Hide → PUT /exercises/{id}/hidden or PUT /muscles/{id}/hidden. GYM-99
 *       now supports hiding own items. On success: close + list invalidation.
 *     - Delete → confirm step (destructive, in-design). On 409 (has history)
 *       offers Hide instead of showing a plain error.
 *   - Global catalog item (`is_mine === false`): Hide only.
 *
 * Design: Bebas Neue for the item-name headline, Sora for action rows. Action
 * rows are full-width, ≥52px, --secondary-bg surface, hairline between rows.
 * Destructive actions use --accent text (graphical use per §9.3). All tokens
 * only (no magic hex). Reduced-motion: BottomSheet already handles slide gating.
 */
import { useState } from "react";
import { useT } from "@/i18n/catalog";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { AddInlineField } from "./AddInlineField";
import { ManageMoveView } from "./ManageMoveView";
import {
    useRenameMuscle,
    useRenameExercise,
    useDeleteMuscle,
    useDeleteExercise,
    useHideMuscle,
    useHideExercise,
    useMoveExercise,
} from "@/hooks/useRecord";
import { useMuscles } from "@/hooks/useAnalytics";
import { ApiError } from "@/api/client";
import { MUSCLE_NAME_MAX, EXERCISE_NAME_MAX } from "@/validation";

type ItemKind = "muscle" | "exercise";
type ManageView = "actions" | "rename" | "confirm-delete" | "offer-hide" | "move";

interface ManageSheetProps {
    /** Whether the sheet is open. */
    open: boolean;
    /** Close the sheet (resets internal view). */
    onClose: () => void;
    /** The item being managed. */
    item: {
        id: number;
        name: string;
        kind: ItemKind;
        /** True = caller's own custom item (rename/delete/move). False = global (hide only). */
        is_mine: boolean;
        /** Muscle name — needed for exercise invalidation. */
        muscleName?: string;
        /** Current muscle id — used to exclude it from the move target list (exercises only). */
        muscleId?: number;
    } | null;
    /**
     * GYM-103: when true, the sheet was opened from the "Show Hidden" expander and
     * should offer only the "Unhide" action (no rename/delete/hide/move).
     */
    isHiddenItem?: boolean;
    /**
     * GYM-103: called when the user confirms "Unhide" in the hidden-item sheet.
     * Must be provided when `isHiddenItem` is true.
     */
    onUnhide?: () => void;
    /** GYM-103: true while the unhide mutation is in-flight. */
    isUnhidePending?: boolean;
}

export function ManageSheet({
    open,
    onClose,
    item,
    isHiddenItem = false,
    onUnhide,
    isUnhidePending = false,
}: ManageSheetProps) {
    const { t, muscle } = useT();
    const [view, setView] = useState<ManageView>("actions");
    const [renameError, setRenameError] = useState<string | null>(null);
    const [deleteError, setDeleteError] = useState<string | null>(null);
    const [moveError, setMoveError] = useState<string | null>(null);
    // GYM-98: track which muscle row is being moved so only that row shows the
    // spinner/"Moving..." label. Other rows stay disabled but not spinning.
    const [movingMuscleId, setMovingMuscleId] = useState<number | null>(null);

    const renameMuscle = useRenameMuscle();
    const renameExercise = useRenameExercise();
    const deleteMuscle = useDeleteMuscle();
    const deleteExercise = useDeleteExercise();
    const hideMuscle = useHideMuscle();
    const hideExercise = useHideExercise();
    const moveExercise = useMoveExercise();

    // Muscle list for the move view — only fetched once (cached), re-used from useMuscles.
    const muscles = useMuscles();

    const isPendingMutation =
        renameMuscle.isPending ||
        renameExercise.isPending ||
        deleteMuscle.isPending ||
        deleteExercise.isPending ||
        hideMuscle.isPending ||
        hideExercise.isPending ||
        moveExercise.isPending;

    function handleClose(): void {
        onClose();
        // Reset view after close animation (BottomSheet returns null when !open)
        setView("actions");
        setRenameError(null);
        setDeleteError(null);
        setMoveError(null);
        setMovingMuscleId(null);
    }

    /**
     * Map a rename failure to its inline message (GYM-126: was duplicated
     * verbatim across the muscle and exercise branches). 409 = name already
     * in use; 422 = the server's validation detail; anything else = generic.
     */
    function renameErrorMessage(err: unknown): string {
        if (err instanceof ApiError) {
            if (err.status === 409) {
                return t("manage.nameInUse");
            }
            if (err.status === 422) {
                // Server validation detail passes through untranslated.
                return typeof (err.detail as { detail?: string })?.detail ===
                    "string"
                    ? (err.detail as { detail: string }).detail
                    : err.message;
            }
        }
        return t("manage.renameError");
    }

    function submitRename(newName: string): void {
        if (!item) return;
        setRenameError(null);
        const callbacks = {
            onSuccess: () => handleClose(),
            onError: (err: unknown) => setRenameError(renameErrorMessage(err)),
        };
        if (item.kind === "muscle") {
            renameMuscle.mutate(
                { muscleId: item.id, body: { name: newName } },
                callbacks,
            );
        } else {
            renameExercise.mutate(
                {
                    exerciseId: item.id,
                    muscleName: item.muscleName ?? "",
                    body: { name: newName },
                },
                callbacks,
            );
        }
    }

    function confirmDelete(): void {
        if (!item) return;
        setDeleteError(null);
        if (item.kind === "muscle") {
            deleteMuscle.mutate(
                { muscleId: item.id },
                {
                    onSuccess: () => handleClose(),
                    onError: (err) => {
                        if (err instanceof ApiError && err.status === 409) {
                            // Has logged history — offer Hide instead.
                            setView("offer-hide");
                            return;
                        }
                        setDeleteError(t("manage.deleteError"));
                    },
                },
            );
        } else {
            deleteExercise.mutate(
                { exerciseId: item.id },
                {
                    onSuccess: () => handleClose(),
                    onError: (err) => {
                        if (err instanceof ApiError && err.status === 409) {
                            setView("offer-hide");
                            return;
                        }
                        setDeleteError(t("manage.deleteError"));
                    },
                },
            );
        }
    }

    function doHide(): void {
        if (!item) return;
        if (item.kind === "muscle") {
            hideMuscle.mutate(
                { muscleId: item.id },
                { onSuccess: () => handleClose() },
            );
        } else {
            hideExercise.mutate(
                { exerciseId: item.id },
                { onSuccess: () => handleClose() },
            );
        }
    }

    function submitMove(targetMuscleId: number, targetMuscleName: string): void {
        if (!item) return;
        setMoveError(null);
        // GYM-98: mark which row is in-flight so only that row shows the spinner.
        setMovingMuscleId(targetMuscleId);
        moveExercise.mutate(
            { exerciseId: item.id, body: { muscle_id: targetMuscleId } },
            {
                onSuccess: () => handleClose(),
                onError: (err) => {
                    // Reset the per-row pending marker on any error so the list
                    // is interactive again (user can retry or pick a different target).
                    setMovingMuscleId(null);
                    if (err instanceof ApiError) {
                        if (err.status === 409) {
                            setMoveError(
                                t("manage.moveCollision", {
                                    muscle: muscle(targetMuscleName),
                                }),
                            );
                            return;
                        }
                        if (err.status === 403) {
                            setMoveError(t("manage.cantMove"));
                            return;
                        }
                        if (err.status === 404) {
                            setMoveError(t("manage.targetNotFound"));
                            return;
                        }
                    }
                    setMoveError(t("move.error"));
                },
            },
        );
    }

    if (!item) return null;

    const maxLength = item.kind === "muscle" ? MUSCLE_NAME_MAX : EXERCISE_NAME_MAX;
    const kindLabel =
        item.kind === "muscle" ? t("label.muscle") : t("label.exercise");
    // Muscle headlines show the localized label; exercises pass through.
    const displayName = item.kind === "muscle" ? muscle(item.name) : item.name;

    return (
        <BottomSheet open={open} onClose={handleClose} titleId="manage-sheet-title" layer="sheet-nested">
            <div className="pb-2">
                {/* Item name as Bebas headline — always visible */}
                <h2
                    id="manage-sheet-title"
                    className="font-display text-title text-text mb-1 truncate"
                    title={displayName}
                >
                    {displayName}
                </h2>
                <p className="text-label text-hint mb-4 uppercase tracking-wide">
                    {kindLabel}
                </p>

                {/* ── GYM-103: UNHIDE view (hidden-item sheet — single action) ── */}
                {view === "actions" && isHiddenItem ? (
                    <div className="rounded-lg border border-hairline overflow-hidden">
                        <button
                            type="button"
                            onClick={onUnhide}
                            disabled={isUnhidePending}
                            className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text disabled:opacity-40"
                        >
                            {isUnhidePending
                                ? t("picker.unhiding")
                                : t("picker.unhide")}
                        </button>
                    </div>
                ) : null}

                {/* ── ACTIONS view ─────────────────────────────────────── */}
                {view === "actions" && !isHiddenItem && (
                    <div className="rounded-lg border border-hairline overflow-hidden">
                        {item.is_mine ? (
                            <>
                                {/* Rename */}
                                <button
                                    type="button"
                                    onClick={() => {
                                        setRenameError(null);
                                        setView("rename");
                                    }}
                                    className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text"
                                >
                                    {t("manage.rename")}
                                </button>
                                {/* Move to another muscle (exercises only) */}
                                {item.kind === "exercise" && (
                                    <>
                                        <div className="h-px bg-hairline" aria-hidden />
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setMoveError(null);
                                                setView("move");
                                            }}
                                            className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text"
                                        >
                                            {t("manage.moveToAnotherMuscle")}
                                        </button>
                                    </>
                                )}
                                {/* GYM-100: Hide also for own items — the only way to declutter
                                    an own item that has logged history (delete returns 409).
                                    GYM-99 extended PUT /exercises/{id}/hidden + /muscles/{id}/hidden
                                    to support own items. */}
                                <div className="h-px bg-hairline" aria-hidden />
                                <button
                                    type="button"
                                    onClick={doHide}
                                    disabled={hideMuscle.isPending || hideExercise.isPending}
                                    className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text disabled:opacity-40"
                                >
                                    {hideMuscle.isPending || hideExercise.isPending
                                        ? t("manage.hiding")
                                        : t("manage.hide")}
                                </button>
                                <div className="h-px bg-hairline" aria-hidden />
                                {/* Delete */}
                                <button
                                    type="button"
                                    onClick={() => {
                                        setDeleteError(null);
                                        setView("confirm-delete");
                                    }}
                                    className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-accent"
                                >
                                    {t("common.delete")}
                                </button>
                            </>
                        ) : (
                            /* Global item — hide only */
                            <button
                                type="button"
                                onClick={doHide}
                                disabled={hideMuscle.isPending || hideExercise.isPending}
                                className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text disabled:opacity-40"
                            >
                                {hideMuscle.isPending || hideExercise.isPending
                                    ? t("manage.hiding")
                                    : t("manage.hide")}
                            </button>
                        )}
                    </div>
                )}

                {/* ── RENAME view ───────────────────────────────────────── */}
                {view === "rename" && (
                    <div className="space-y-3">
                        <button
                            type="button"
                            onClick={() => {
                                setView("actions");
                                setRenameError(null);
                            }}
                            className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
                        >
                            ← {t("common.back")}
                        </button>
                        <AddInlineField
                            placeholder={
                                item.kind === "muscle"
                                    ? t("manage.newMuscleName")
                                    : t("manage.newExerciseName")
                            }
                            actionLabel={t("common.save")}
                            maxLength={maxLength}
                            initialValue={item.name}
                            pending={renameMuscle.isPending || renameExercise.isPending}
                            error={renameError}
                            onSubmit={submitRename}
                            onCancel={() => {
                                setView("actions");
                                setRenameError(null);
                            }}
                        />
                    </div>
                )}

                {/* ── CONFIRM DELETE view ───────────────────────────────── */}
                {view === "confirm-delete" && (
                    <div className="space-y-3">
                        <p className="text-base text-text">
                            {t("manage.deleteConfirm", { name: displayName })}
                        </p>
                        {deleteError ? (
                            <p className="text-label text-accent">{deleteError}</p>
                        ) : null}
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => {
                                    setView("actions");
                                    setDeleteError(null);
                                }}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg border border-hairline bg-secondary-bg text-base text-text disabled:opacity-40"
                            >
                                {t("common.cancel")}
                            </button>
                            <button
                                type="button"
                                onClick={confirmDelete}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg bg-accent text-base font-semibold text-button-text disabled:opacity-40"
                            >
                                {deleteMuscle.isPending || deleteExercise.isPending
                                    ? t("manage.deleting")
                                    : t("common.delete")}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── OFFER HIDE view (409 — has history) ──────────────── */}
                {view === "offer-hide" && (
                    <div className="space-y-3">
                        <p className="text-base text-text">
                            {t("manage.hasHistory", { name: displayName })}
                        </p>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => setView("actions")}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg border border-hairline bg-secondary-bg text-base text-text disabled:opacity-40"
                            >
                                {t("common.cancel")}
                            </button>
                            <button
                                type="button"
                                onClick={doHide}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg bg-accent text-base font-semibold text-button-text disabled:opacity-40"
                            >
                                {hideMuscle.isPending || hideExercise.isPending
                                    ? t("manage.hiding")
                                    : t("manage.hideAction")}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── MOVE view (GYM-90, extracted in GYM-127) ──────────── */}
                {view === "move" && (
                    <ManageMoveView
                        muscles={muscles.data ?? []}
                        musclesLoading={muscles.isLoading}
                        excludeMuscleId={item.muscleId}
                        moveError={moveError}
                        movingMuscleId={movingMuscleId}
                        movePending={moveExercise.isPending}
                        onBack={() => {
                            setView("actions");
                            setMoveError(null);
                        }}
                        onMove={submitMove}
                    />
                )}
            </div>
        </BottomSheet>
    );
}
