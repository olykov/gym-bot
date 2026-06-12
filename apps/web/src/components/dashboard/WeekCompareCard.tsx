/**
 * THIS WEEK card (GYM-136, doc 03 §4.3) — a compact one-card week summary on
 * the Dashboard, under <SummaryCards> and above <ActivityGrid>:
 *
 *   THIS WEEK                       (uppercase --hint label)
 *   24 sets · 5,840 kg              (Bebas tabular figures, inline)
 *   ▲ +3 sets · ▲ +420 kg           (deltas vs last week — GYM-130 language:
 *                                    accent up, hint down, zero omitted)
 *
 * Mounted only on the Dashboard's has-data path (the new-user EmptyState
 * branch never renders it, so the empty path fires no query — ARCH §2).
 * The render model (hidden / first-week / compare) lives in
 * weekCompareModel.ts; this component is markup only.
 *
 * Quiet failure: an error renders nothing — this is a secondary surface and
 * must not add an error card under a healthy dashboard.
 */
import type { ReactNode } from "react";
import { useT } from "@/i18n/catalog";
import { Card } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { useWeekCompare } from "@/hooks/useAnalytics";
import {
    buildWeekCompareModel,
    type WeekCompareModel,
    type WeekDelta,
} from "./weekCompareModel";

/** Shared figure styling: accent when up, quiet hint when down (never red). */
function deltaClass(delta: WeekDelta): string {
    return `tabular text-label ${
        delta.kind === "up" ? "font-semibold text-accent" : "text-hint"
    }`;
}

/** The sets-count delta figure (plural-aware via the catalog). */
function SetsDeltaFigure({ delta }: { delta: WeekDelta }) {
    const { tp } = useT();
    return (
        <span className={deltaClass(delta)}>
            {tp(
                delta.kind === "up" ? "weekDelta.upSets" : "weekDelta.downSets",
                delta.amount,
            )}
        </span>
    );
}

/** The volume delta figure (locale-grouped, one fraction digit max). */
function VolumeDeltaFigure({ delta }: { delta: WeekDelta }) {
    const { t, locale } = useT();
    const amount = new Intl.NumberFormat(locale, {
        maximumFractionDigits: 1,
    }).format(delta.amount);
    return (
        <span className={deltaClass(delta)}>
            {t(
                delta.kind === "up"
                    ? "weekDelta.upVolume"
                    : "weekDelta.downVolume",
                { amount },
            )}
        </span>
    );
}

/** Non-zero deltas only (GYM-132 restraint: never "▲ 0"). */
function deltaNodes(model: WeekCompareModel): { key: string; node: ReactNode }[] {
    if (model.kind !== "compare") return [];
    const nodes: { key: string; node: ReactNode }[] = [];
    if (model.setsDelta && model.setsDelta.kind !== "eq") {
        nodes.push({
            key: "sets",
            node: <SetsDeltaFigure delta={model.setsDelta} />,
        });
    }
    if (model.volumeDelta && model.volumeDelta.kind !== "eq") {
        nodes.push({
            key: "volume",
            node: <VolumeDeltaFigure delta={model.volumeDelta} />,
        });
    }
    return nodes;
}

export function WeekCompareCard() {
    const { t, tp, locale } = useT();
    const wc = useWeekCompare();

    if (wc.isLoading) return <SkeletonCard />;
    // Secondary surface: stay quiet on error (no second error card).
    if (wc.isError || !wc.data) return null;

    const model = buildWeekCompareModel(wc.data);
    if (model.kind === "hidden") return null;

    // Locale-grouped volume figure; ×2.5kg weights can produce a half-kilo.
    const volumeFigure = new Intl.NumberFormat(locale, {
        maximumFractionDigits: 1,
    }).format(model.volume);
    const deltas = deltaNodes(model);

    return (
        <Card>
            <span className="text-label uppercase tracking-wide text-hint">
                {t("weekCompare.title")}
            </span>
            <div className="tabular mt-1 font-display text-title leading-none text-text">
                {tp("count.sets", model.sets)} ·{" "}
                {t("weekCompare.volume", { volume: volumeFigure })}
            </div>
            {deltas.length > 0 ? (
                <p
                    className="mt-2 flex items-center gap-2"
                    aria-label={t("weekCompare.vsLastAria")}
                >
                    {deltas.map(({ key, node }, i) => (
                        <span key={key} className="flex items-center gap-2">
                            {i > 0 ? (
                                <span className="text-label text-hint">·</span>
                            ) : null}
                            {node}
                        </span>
                    ))}
                </p>
            ) : null}
        </Card>
    );
}
