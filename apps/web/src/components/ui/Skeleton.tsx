/**
 * Token-driven shimmer block + compositions (spec §10.4).
 * Every TanStack Query `isLoading` renders one of these (never a spinner), and
 * the shape matches the final layout so there is no jump. The shimmer animation
 * is disabled under prefers-reduced-motion (see index.css).
 */
import { Card } from "./Card";

interface SkeletonProps {
    className?: string;
    /** Inline width/height when a utility class isn't enough. */
    style?: React.CSSProperties;
}

export function Skeleton({ className = "", style }: SkeletonProps) {
    return <div className={`shimmer rounded ${className}`} style={style} aria-hidden />;
}

/** Matches a <StatCard>: a big number block over a short label. */
export function SkeletonCard() {
    return (
        <Card>
            <Skeleton className="h-8 w-16" />
            <Skeleton className="mt-2 h-3 w-20" />
        </Card>
    );
}

/** Grey activity squares — matches <ActivityGrid> (GYM-42). */
export function SkeletonGrid() {
    return (
        <Card>
            <Skeleton className="mb-3 h-4 w-28" />
            <div className="flex gap-1">
                {Array.from({ length: 8 }).map((_, col) => (
                    <div key={col} className="flex flex-col gap-1">
                        {Array.from({ length: 7 }).map((__, row) => (
                            <Skeleton key={row} className="h-3 w-3 rounded-sm" />
                        ))}
                    </div>
                ))}
            </div>
        </Card>
    );
}

/** Matches <ExerciseProgressChart> (GYM-42). */
export function SkeletonChart() {
    return (
        <Card>
            <Skeleton className="mb-3 h-4 w-32" />
            <Skeleton className="h-44 w-full" />
        </Card>
    );
}
