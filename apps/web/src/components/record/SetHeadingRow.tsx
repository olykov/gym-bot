/**
 * The SET/PR heading row of the SetLogger controls region — extracted from
 * SetLogger.tsx in GYM-135 (file-size split, behavior preserved):
 *
 *  - "SET {n}" heading — only the digit rolls on advance (GYM-131 #4); the
 *    catalog template is split around {n} so the words stay i18n'd.
 *  - GYM-135 trend group (sparkline + `▲ 8w` chip) — strictly secondary,
 *    placed LEFT of the PR chip so the PR stays the dominant right anchor.
 *    Renders nothing without ≥3 trend points (TrendSparkline owns the read).
 *  - PR target chip — `PR {w}kg × {r}`; pulses on a weight-PR beat.
 *
 * At narrow widths (360px) the heading is the flexible child (min-w-0 +
 * truncate); the trend group and PR chip stay intact (shrink-0).
 */
import { useMemo } from "react";
import { useT } from "@/i18n/catalog";
import { MESSAGES } from "@/i18n/messages";
import { RollingNumber } from "@/components/ui/RollingNumber";
import type { EffectivePR } from "./derive";
import { TrendSparkline } from "./TrendSparkline";

interface SetHeadingRowProps {
    /** The set number about to be logged (the heading digit). */
    nextSet: number;
    /** The derived PR chip model (GYM-104), or null when nothing is known. */
    effectivePR: EffectivePR | null;
    /** GYM-131: true while the PR-beat pulse animation is live. */
    pulse: boolean;
    /** Canonical muscle name — the trend query key part. */
    muscleName: string;
    /** Exercise name — the trend query key part. */
    exerciseName: string;
}

export function SetHeadingRow({
    nextSet,
    effectivePR,
    pulse,
    muscleName,
    exerciseName,
}: SetHeadingRowProps) {
    const { t, locale } = useT();

    // GYM-131 #4: split the catalog template around {n} so <RollingNumber>
    // animates the digit while the words stay translated.
    const [setHeadingBefore = "", setHeadingAfter = ""] = useMemo(
        () => MESSAGES["logger.setHeading"][locale].split("{n}"),
        [locale],
    );

    return (
        <div className="mt-4 flex items-center justify-between gap-2">
            <h3 className="min-w-0 truncate font-display text-title text-text">
                {setHeadingBefore}
                <RollingNumber value={nextSet} />
                {setHeadingAfter}
            </h3>
            <div className="flex shrink-0 items-center gap-2">
                <TrendSparkline muscle={muscleName} exercise={exerciseName} />
                {effectivePR !== null ? (
                    <span
                        className={`tabular rounded-full px-3 py-1 text-label font-semibold text-accent ${
                            pulse ? "pr-pulse motion-reduce:animate-none" : ""
                        }`}
                    >
                        {t("logger.prValue", { weight: effectivePR.weight })}
                        {effectivePR.reps !== null
                            ? ` × ${effectivePR.reps}`
                            : ""}
                    </span>
                ) : null}
            </div>
        </div>
    );
}
