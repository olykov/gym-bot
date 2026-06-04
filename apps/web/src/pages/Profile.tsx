/**
 * Profile (stub) — spec §12.1.
 *
 * We design the SLOT, not the screen: a real `/profile` route that renders
 * inside the one `<AppShell>` (no own chrome) and shows a single `<EmptyState>`.
 * It fires ZERO queries (the empty path must be the cheapest, ARCH §2 / §0).
 * The actual profile feature is a separate task.
 */
import { EmptyState } from "@/components/ui/EmptyState";

export function Profile() {
    return <EmptyState title="PROFILE" subtitle="Coming soon" />;
}
