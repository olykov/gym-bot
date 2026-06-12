/**
 * GYM-132 — the session summary shown on Done (doc 03 §3, operator decision
 * #3: it must NOT lengthen the fast logging experience — the constraints ARE
 * the spec):
 *
 *  - Rendered only via the explicit Done button with ≥1 set logged this
 *    session (RecordSheet decides; 0 sets → instant close, no summary ever).
 *  - 100% from in-memory data: the cross-exercise session log accumulated by
 *    RecordSheet + the ALREADY-CACHED `/analytics/summary` snapshot for the
 *    week-streak line (qc.getQueryData — never a fetch; the line is omitted
 *    entirely on a cache miss). ZERO network, NO loading state, no spinner.
 *  - Dismiss = ONE tap anywhere: the whole panel is a single <button>
 *    (scrim / Telegram Back / drag stay available as usual via BottomSheet),
 *    plus an auto-dismiss timer (~4s, cleared on unmount). The timer is not
 *    motion — it runs under prefers-reduced-motion too.
 *  - Fits 360px without scrolling: four short lines + the tap-to-close hint.
 *  - Restrained tone — an account, not a celebration (no exclamation marks).
 *
 * Closing always goes through the SAME onDismiss → RecordSheet onClose, so
 * the §12.5 cross-screen invalidation contract is untouched (it fires per
 * save in useCreateTraining, not on close).
 */
import { useEffect, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useT } from "@/i18n/catalog";
import { queryKeys } from "@/api/queryKeys";
import type { AnalyticsSummary } from "@/api/analytics";
import { summarizeSession, type SessionLogEntry } from "./derive";

/** Auto-dismiss window — a timer, not motion (kept under reduced motion). */
const SUMMARY_AUTO_DISMISS_MS = 4000;

interface SessionSummaryPanelProps {
    /** The session log RecordSheet accumulated (length ≥ 1 by contract). */
    log: SessionLogEntry[];
    /** The one close path — RecordSheet's onClose (§12.5 contract kept). */
    onDismiss: () => void;
}

export function SessionSummaryPanel({
    log,
    onDismiss,
}: SessionSummaryPanelProps) {
    const { t, tp, locale } = useT();
    const qc = useQueryClient();
    const summary = useMemo(() => summarizeSession(log), [log]);

    // Cache-only read — getQueryData never fetches (zero-network constraint).
    const cachedSummary = qc.getQueryData<AnalyticsSummary>(
        queryKeys.analytics.summary(),
    );

    useEffect(() => {
        const timer = window.setTimeout(onDismiss, SUMMARY_AUTO_DISMISS_MS);
        return () => window.clearTimeout(timer);
    }, [onDismiss]);

    // Locale-grouped volume figure (e.g. "5,840" / "5 840"); ×2.5kg weights
    // can produce a half-kilo, so allow one fraction digit.
    const volumeFigure = useMemo(
        () =>
            new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(
                summary.volume,
            ),
        [locale, summary.volume],
    );

    const statsLine = `${tp("count.sets", summary.sets)} · ${tp(
        "count.exercises",
        summary.exercises,
    )} · ${t("sessionSummary.volume", { volume: volumeFigure })}`;

    // "▲ N sets beat last session · M PR" — each part only when non-zero
    // (never "▲ 0 sets…"; an even session simply shows no progress line).
    const beatParts: string[] = [];
    if (summary.beatLast > 0) {
        beatParts.push(tp("sessionSummary.beatLast", summary.beatLast));
    }
    if (summary.prs > 0) {
        beatParts.push(t("sessionSummary.prCount", { n: summary.prs }));
    }

    return (
        // The WHOLE panel is the dismiss button (one tap anywhere). Spans
        // (block) instead of h*/p — a <button> allows phrasing content only.
        <button
            type="button"
            onClick={onDismiss}
            className="flex min-h-0 w-full flex-1 flex-col items-center justify-center gap-3 pb-6 text-center"
        >
            <span className="block font-display text-title text-text">
                {t("sessionSummary.title")}
            </span>
            <span className="tabular block font-display text-title text-text">
                {statsLine}
            </span>
            {beatParts.length > 0 ? (
                <span className="tabular block text-label font-semibold text-accent">
                    {beatParts.join(" · ")}
                </span>
            ) : null}
            {cachedSummary ? (
                <span className="tabular block text-base text-hint">
                    {t("sessionSummary.weekStreak", {
                        n: cachedSummary.current_streak,
                    })}
                </span>
            ) : null}
            <span className="mt-2 block text-label text-hint">
                {t("sessionSummary.tapToClose")}
            </span>
        </button>
    );
}
