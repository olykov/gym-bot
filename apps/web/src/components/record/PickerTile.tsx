/**
 * The one picker tile (GYM-126) — merges the formerly byte-identical
 * MuscleTile / ExerciseTile pair (GYM-82) and HiddenMuscleTile /
 * HiddenExerciseTile pair (GYM-103) from RecordPicker.tsx.
 *
 * Variants:
 *  - default: hairline border on --secondary-bg, --text label, press feedback;
 *    tap selects, long-press opens the manage sheet.
 *  - muted (hidden item): dashed border, --hint label at opacity-70; tap does
 *    nothing (hidden items can't be picked — they're not visible in the
 *    catalog), long-press opens the Unhide manage sheet. While the unhide
 *    mutation is in-flight the tile disables and reads "Unhiding…".
 *
 * Both variants: fixed --tile-h height (`h-tile`), 3-line clamped name
 * (.tile-name), and tile-no-select so a long-press never triggers native text
 * selection (the GYM-82 haptic manage-sheet fires instead).
 */
import { useT } from "@/i18n/catalog";
import { useTilePressHandlers } from "./useTilePressHandlers";

interface PickerTileProps {
    name: string;
    tabIndex: number;
    /** Long-press → the manage sheet (both variants). */
    onLongPress: () => void;
    /** Tap → select. Default variant only; the muted variant ignores taps. */
    onTap?: () => void;
    /** Muted hidden-item variant (GYM-103). */
    muted?: boolean;
    /** Muted variant: true while THIS item's unhide mutation is in-flight. */
    isPending?: boolean;
}

export function PickerTile({
    name,
    tabIndex,
    onLongPress,
    onTap,
    muted = false,
    isPending = false,
}: PickerTileProps) {
    const { t } = useT();
    const pressHandlers = useTilePressHandlers(
        onTap ?? (() => undefined),
        onLongPress,
    );

    if (muted) {
        return (
            <button
                type="button"
                tabIndex={tabIndex}
                title={name}
                disabled={isPending}
                {...pressHandlers}
                className="tile-no-select flex h-tile w-full items-center justify-center rounded-lg border border-dashed border-hairline px-3 text-center text-base text-hint opacity-70 disabled:opacity-40"
            >
                <span className="tile-name">
                    {isPending ? t("picker.unhiding") : name}
                </span>
            </button>
        );
    }

    return (
        <button
            type="button"
            tabIndex={tabIndex}
            title={name}
            {...pressHandlers}
            className="tile-no-select press-95 flex h-tile w-full items-center justify-center rounded-lg border border-hairline bg-secondary-bg px-3 text-center text-base text-text"
        >
            <span className="tile-name">{name}</span>
        </button>
    );
}
