/**
 * 2×2 dashboard summary (spec §10.2) — Exercises · Sets · PRs · Streak from
 * `/analytics/summary`. Big Bebas numeral counts up on first load (skipped on a
 * cache hit and under reduced motion, see useCountUp). The PRs card is the
 * `--accent` hero with a PR chip.
 */
import { useT } from "@/i18n/catalog";
import { StatCard, StatChip } from "@/components/ui/StatCard";
import { useCountUp } from "@/hooks/useCountUp";
import type { AnalyticsSummary } from "@/api/analytics";

interface SummaryCardsProps {
    summary: AnalyticsSummary;
    /** Count up once (false on a cache hit, so cached dashboards don't re-run). */
    animate: boolean;
}

export function SummaryCards({ summary, animate }: SummaryCardsProps) {
    const { t } = useT();
    return (
        <div className="grid grid-cols-2 gap-4">
            <StatCard
                value={<Num value={summary.exercises} animate={animate} />}
                label={t("summary.exercises")}
            />
            <StatCard
                value={<Num value={summary.sets} animate={animate} />}
                label={t("summary.sets")}
            />
            <StatCard
                value={<Num value={summary.prs} animate={animate} />}
                label={t("summary.prs")}
                accent
                chip={<StatChip>{t("pr")}</StatChip>}
            />
            <StatCard
                value={<Num value={summary.current_streak} animate={animate} />}
                label={t("summary.weekStreak")}
            />
        </div>
    );
}

/** A single count-up numeral (the rendered value lives inside StatCard's slot). */
function Num({ value, animate }: { value: number; animate: boolean }) {
    const shown = useCountUp(value, animate);
    return <>{shown}</>;
}
