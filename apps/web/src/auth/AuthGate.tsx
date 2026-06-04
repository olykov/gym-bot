/**
 * Renders the app only once a session exists. Pending shows a skeleton-filled
 * shell frame (no spinner, spec §10.4); error shows the shared ErrorState with
 * retry; outside Telegram it explains the situation rather than looping auth.
 */
import type { ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard, SkeletonGrid } from "@/components/ui/Skeleton";

/** A bare, scrollable centered frame for pre-shell states (no nav yet). */
function Frame({ children }: { children: ReactNode }) {
    return (
        <div className="flex min-h-full items-start justify-center bg-secondary-bg">
            <div className="w-full max-w-container px-4 py-8">{children}</div>
        </div>
    );
}

export function AuthGate({ children }: { children: ReactNode }) {
    const { status, error, retry } = useAuth();

    if (status === "authed" || status === "no-telegram") {
        // no-telegram still mounts the shell so the design is reviewable in a
        // plain browser; authed calls will 401 there, handled per-query later.
        return <>{children}</>;
    }

    if (status === "error") {
        return (
            <Frame>
                <ErrorState
                    message={error ?? "Could not sign you in via Telegram."}
                    onRetry={retry}
                />
            </Frame>
        );
    }

    // pending
    return (
        <Frame>
            <div className="flex flex-col gap-4">
                <EmptyState title="Loading" subtitle="Signing you in…" />
                <div className="grid grid-cols-2 gap-4">
                    <SkeletonCard />
                    <SkeletonCard />
                </div>
                <SkeletonGrid />
            </div>
        </Frame>
    );
}
