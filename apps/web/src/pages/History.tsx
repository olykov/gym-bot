/**
 * History route (spec §11.2) — a reverse-chronological <DayCard> list from
 * `GET /training/days`, window-based pagination (NOT offset).
 *
 * v1 default window = the last ~12 weeks; an IntersectionObserver sentinel near
 * the list bottom expands the window backward another step (and a "Load earlier"
 * Card-styled button is the non-JS / reduced-motion fallback). The list re-queries
 * per window key and caches; we stop expanding once a window yields no new earliest
 * day (the user's first training).
 *
 * States are first-class (§10.4 / §11.6): SkeletonCard×5 shaped like a DayCard,
 * an EmptyState for the no-trainings new-user path, an inline ErrorState + retry,
 * and a quiet "That's the beginning." footer when the window is exhausted.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { DayCard } from "@/components/ui/DayCard";
import { useTrainingDays } from "@/hooks/useTraining";
import { windowForSteps } from "@/components/history/historyWindow";

export function History() {
    // Expandable window: `steps` grows backward; `to` stays today.
    const [steps, setSteps] = useState(1);
    const { from, to } = useMemo(() => windowForSteps(steps), [steps]);

    const days = useTrainingDays(from, to);

    // Track the previous earliest day to detect "no new day" (window exhausted).
    const prevEarliest = useRef<string | null>(null);
    const [exhausted, setExhausted] = useState(false);

    useEffect(() => {
        // Only evaluate exhaustion on FRESH data for the current window. While
        // keepPreviousData holds the prior list (isPlaceholderData), days.data
        // still belongs to the older window — comparing it would falsely mark
        // the list exhausted on every load-more (GYM-53 #4).
        if (!days.data || days.isPlaceholderData) return;
        const earliest = days.data.length
            ? days.data[days.data.length - 1].date
            : null;
        // After an expand, if the earliest day didn't move further back, stop.
        if (steps > 1 && earliest === prevEarliest.current) {
            setExhausted(true);
        }
        prevEarliest.current = earliest;
    }, [days.data, days.isPlaceholderData, steps]);

    function loadEarlier(): void {
        if (!exhausted && !days.isFetching) setSteps((s) => s + 1);
    }

    if (days.isLoading) {
        return (
            <>
                {Array.from({ length: 5 }).map((_, i) => (
                    <DayCardSkeleton key={i} />
                ))}
            </>
        );
    }

    if (days.isError) {
        return <ErrorState onRetry={() => days.refetch()} />;
    }

    const list = days.data ?? [];

    if (list.length === 0) {
        return (
            <EmptyState
                title="No trainings yet"
                subtitle="Log a set in the bot and it shows up here."
            />
        );
    }

    return (
        <>
            {list.map((day) => (
                <DayCard key={day.date} day={day} />
            ))}

            <ListTail
                exhausted={exhausted}
                fetching={days.isFetching}
                onLoadEarlier={loadEarlier}
            />
        </>
    );
}

/** Sentinel + fallback button + exhausted footer (spec §11.2). */
function ListTail({
    exhausted,
    fetching,
    onLoadEarlier,
}: {
    exhausted: boolean;
    fetching: boolean;
    onLoadEarlier: () => void;
}) {
    const sentinel = useRef<HTMLDivElement>(null);

    // IntersectionObserver: expand the window when the sentinel scrolls into view.
    useEffect(() => {
        if (exhausted) return;
        const el = sentinel.current;
        if (!el || typeof IntersectionObserver === "undefined") return;
        const io = new IntersectionObserver(
            (entries) => {
                if (entries[0]?.isIntersecting) onLoadEarlier();
            },
            { rootMargin: "200px" },
        );
        io.observe(el);
        return () => io.disconnect();
    }, [exhausted, onLoadEarlier]);

    if (exhausted) {
        return (
            <p className="py-4 text-center text-label text-hint">
                That's the beginning.
            </p>
        );
    }

    return (
        <>
            <div ref={sentinel} aria-hidden className="h-1" />
            {/* Non-JS / reduced-motion fallback. */}
            <Card
                role="button"
                tabIndex={0}
                onClick={onLoadEarlier}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onLoadEarlier();
                    }
                }}
                className="press-95 cursor-pointer text-center text-base text-hint"
            >
                {fetching ? "Loading…" : "Load earlier"}
            </Card>
        </>
    );
}

/** A SkeletonCard shaped like <DayCard> (Bebas heading bar, chips, hint line). */
function DayCardSkeleton() {
    return (
        <Card className="flex items-center gap-4">
            <div className="flex-1">
                <Skeleton className="h-6 w-32" />
                <div className="mt-2 flex gap-2">
                    <Skeleton className="h-6 w-16 rounded-full" />
                    <Skeleton className="h-6 w-16 rounded-full" />
                </div>
                <Skeleton className="mt-2 h-3 w-40" />
            </div>
            <Skeleton className="h-5 w-5 rounded" />
        </Card>
    );
}
