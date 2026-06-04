/**
 * Dashboard route (spec §10.2) — <SummaryCards> (2×2) + <ActivityGrid> from the
 * `/analytics/summary` and `/analytics/activity` reads.
 *
 * States are first-class (§10.4): a layout-matching skeleton while loading, an
 * inline ErrorState + retry on failure, and a single new-user EmptyState when
 * the caller has logged nothing (no extra queries fired on that path). Count-up
 * runs only when the summary loaded fresh this mount (cache hit → no re-count).
 */
import { useMemo } from "react";
import { SkeletonCard, SkeletonGrid } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { ActivityGrid } from "@/components/dashboard/ActivityGrid";
import { useActivity, useSummary } from "@/hooks/useAnalytics";
import { windowRange } from "@/components/dashboard/activityGridModel";

export function Dashboard() {
    // The 26-week MVP window (Monday-first), computed once per mount.
    const { from, to } = useMemo(() => windowRange(), []);

    const summary = useSummary();
    const activity = useActivity(from, to);

    // Loading: skeletons that match the final layout (no spinner / jump).
    if (summary.isLoading || activity.isLoading) {
        return (
            <>
                <div className="grid grid-cols-2 gap-4">
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                </div>
                <SkeletonGrid />
            </>
        );
    }

    // Error: one inline surface + retry per failed query.
    if (summary.isError) {
        return <ErrorState onRetry={() => summary.refetch()} />;
    }
    if (activity.isError) {
        return <ErrorState onRetry={() => activity.refetch()} />;
    }

    const s = summary.data;
    const days = activity.data ?? [];

    // New user: nothing logged ever. One EmptyState; no further queries fire.
    const isNewUser = s != null && s.sets === 0 && days.length === 0;
    if (isNewUser) {
        return (
            <EmptyState
                title="No trainings yet"
                subtitle="Log a workout in the bot and your activity will show up here."
            />
        );
    }

    return (
        <>
            {s ? (
                <SummaryCards
                    summary={s}
                    animate={summary.isFetchedAfterMount}
                />
            ) : null}
            <ActivityGrid days={days} />
        </>
    );
}
