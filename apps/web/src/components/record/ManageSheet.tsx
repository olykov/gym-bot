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
 *   - Own custom item (`is_mine === true`): Rename + Move to another muscle + Delete.
 *     - Rename → inline edit reusing AddInlineField pattern, pre-filled, enforces
 *       maxLength. 409 (dup name) → graceful inline message; 422 → server message.
 *     - Move (exercises only, GYM-90) → muscle list (all visible muscles, excluding
 *       the current one). Picking a target calls PATCH /exercises/{id}/muscle.
 *       On success: close + full invalidation. 409 (name collision in target) →
 *       graceful inline message, stay in move view. 403/404 → graceful error.
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
import { BottomSheet } from "@/components/ui/BottomSheet";
import { AddInlineField } from "./AddInlineField";
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
}

export function ManageSheet({ open, onClose, item }: ManageSheetProps) {
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

    function submitRename(newName: string): void {
        if (!item) return;
        setRenameError(null);
        if (item.kind === "muscle") {
            renameMuscle.mutate(
                { muscleId: item.id, body: { name: newName } },
                {
                    onSuccess: () => handleClose(),
                    onError: (err) => {
                        if (err instanceof ApiError) {
                            if (err.status === 409) {
                                setRenameError("That name is already in use.");
                                return;
                            }
                            if (err.status === 422) {
                                const detail =
                                    typeof (err.detail as { detail?: string })?.detail ===
                                    "string"
                                        ? (err.detail as { detail: string }).detail
                                        : err.message;
                                setRenameError(detail);
                                return;
                            }
                        }
                        setRenameError("Couldn't rename — try again.");
                    },
                },
            );
        } else {
            renameExercise.mutate(
                {
                    exerciseId: item.id,
                    muscleName: item.muscleName ?? "",
                    body: { name: newName },
                },
                {
                    onSuccess: () => handleClose(),
                    onError: (err) => {
                        if (err instanceof ApiError) {
                            if (err.status === 409) {
                                setRenameError("That name is already in use.");
                                return;
                            }
                            if (err.status === 422) {
                                const detail =
                                    typeof (err.detail as { detail?: string })?.detail ===
                                    "string"
                                        ? (err.detail as { detail: string }).detail
                                        : err.message;
                                setRenameError(detail);
                                return;
                            }
                        }
                        setRenameError("Couldn't rename — try again.");
                    },
                },
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
                        setDeleteError("Couldn't delete — try again.");
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
                        setDeleteError("Couldn't delete — try again.");
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
                                `You already have an exercise with this name in ${targetMuscleName}.`,
                            );
                            return;
                        }
                        if (err.status === 403) {
                            setMoveError("This exercise can't be moved.");
                            return;
                        }
                        if (err.status === 404) {
                            setMoveError("Target muscle not found — try again.");
                            return;
                        }
                    }
                    setMoveError("Couldn't move — try again.");
                },
            },
        );
    }

    if (!item) return null;

    const maxLength = item.kind === "muscle" ? MUSCLE_NAME_MAX : EXERCISE_NAME_MAX;
    const kindLabel = item.kind === "muscle" ? "Muscle" : "Exercise";

    return (
        <BottomSheet open={open} onClose={handleClose} titleId="manage-sheet-title" zIndex={40}>
            <div className="pb-2">
                {/* Item name as Bebas headline — always visible */}
                <h2
                    id="manage-sheet-title"
                    className="font-display text-title text-text mb-1 truncate"
                    title={item.name}
                >
                    {item.name}
                </h2>
                <p className="text-label text-hint mb-4 uppercase tracking-wide">
                    {kindLabel}
                </p>

                {/* ── ACTIONS view ─────────────────────────────────────── */}
                {view === "actions" && (
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
                                    Rename
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
                                            Move to another muscle
                                        </button>
                                    </>
                                )}
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
                                    Delete
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
                                    ? "Hiding…"
                                    : "Hide from my list"}
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
                            ← Back
                        </button>
                        <AddInlineField
                            placeholder={`New ${item.kind} name`}
                            actionLabel="Save"
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
                            Delete{" "}
                            <span className="font-semibold">"{item.name}"</span>? This
                            cannot be undone.
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
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={confirmDelete}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg bg-accent text-base font-semibold text-button-text disabled:opacity-40"
                            >
                                {deleteMuscle.isPending || deleteExercise.isPending
                                    ? "Deleting…"
                                    : "Delete"}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── OFFER HIDE view (409 — has history) ──────────────── */}
                {view === "offer-hide" && (
                    <div className="space-y-3">
                        <p className="text-base text-text">
                            <span className="font-semibold">"{item.name}"</span> has
                            logged history and can't be deleted. Hide it from your
                            picker instead?
                        </p>
                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={() => setView("actions")}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg border border-hairline bg-secondary-bg text-base text-text disabled:opacity-40"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={doHide}
                                disabled={isPendingMutation}
                                className="press-95 flex-1 min-h-[48px] rounded-lg bg-accent text-base font-semibold text-button-text disabled:opacity-40"
                            >
                                {hideMuscle.isPending || hideExercise.isPending
                                    ? "Hiding…"
                                    : "Hide"}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── MOVE view (GYM-90) ────────────────────────────────── */}
                {view === "move" && (
                    <div className="space-y-3">
                        <button
                            type="button"
                            onClick={() => {
                                setView("actions");
                                setMoveError(null);
                            }}
                            className="press-95 -ml-1 inline-flex min-h-[44px] items-center gap-1 px-1 text-base text-hint"
                        >
                            ← Back
                        </button>
                        <p className="text-label uppercase tracking-wide text-hint">
                            Move to
                        </p>
                        {moveError ? (
                            <p className="text-label text-accent">{moveError}</p>
                        ) : null}
                        <div className="rounded-lg border border-hairline overflow-hidden">
                            {(muscles.data ?? [])
                                .filter((m) => m.id !== item.muscleId)
                                .map((m, idx, arr) => {
                                    const isThisRowMoving = movingMuscleId === m.id;
                                    return (
                                        <div key={m.id}>
                                            <button
                                                type="button"
                                                onClick={() => submitMove(m.id, m.name)}
                                                disabled={moveExercise.isPending}
                                                className="press-95 flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-left text-base text-text disabled:opacity-40"
                                            >
                                                {isThisRowMoving ? "Moving…" : m.name}
                                            </button>
                                            {idx < arr.length - 1 && (
                                                <div className="h-px bg-hairline" aria-hidden />
                                            )}
                                        </div>
                                    );
                                })}
                            {muscles.isLoading && (
                                <div className="flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-base text-hint">
                                    Loading…
                                </div>
                            )}
                            {!muscles.isLoading &&
                                (muscles.data ?? []).filter((m) => m.id !== item.muscleId)
                                    .length === 0 && (
                                    <div className="flex w-full items-center min-h-[52px] px-4 bg-secondary-bg text-base text-hint">
                                        No other muscles available.
                                    </div>
                                )}
                        </div>
                    </div>
                )}
            </div>
        </BottomSheet>
    );
}
