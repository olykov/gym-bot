/**
 * The one set figure (GYM-126) — the trailing `{weight}kg × {reps}` display
 * typography shared by <SetRow> (history day detail, §11.3) and the SetLogger
 * recap rows (§12.3). Bebas display face, tabular-nums so stacked rows align.
 *
 * When weight/reps are unknown (a pre-session set whose numbers the
 * log-context doesn't carry) it renders the muted `— · —` placeholder in the
 * same figure style — honest, never fabricated (GYM-123 #3).
 *
 * GYM-130: `ghost` renders the figure in --hint at ~70% opacity — the
 * LAST TIME column of the comparison recap (the previous session's set).
 */
import { useT } from "@/i18n/catalog";

interface SetFigureProps {
    /** Weight in kg; null = unknown (renders the muted placeholder). */
    weight: number | null;
    /** Reps; null = unknown (renders the muted placeholder). */
    reps: number | null;
    /** GYM-130: ghost (last-session) styling — --hint, ~70% opacity. */
    ghost?: boolean;
}

export function SetFigure({ weight, reps, ghost = false }: SetFigureProps) {
    const { t } = useT();
    if (weight !== null && reps !== null) {
        return (
            <span
                className={`tabular font-display text-title leading-none ${
                    ghost ? "text-hint opacity-70" : "text-text"
                }`}
            >
                {t("figure.weightReps", { weight, reps })}
            </span>
        );
    }
    return (
        <span className="tabular font-display text-title leading-none text-hint">
            — · —
        </span>
    );
}
