/**
 * Dashboard route — placeholder shell content (GYM-41). The real
 * ActivityGrid + SummaryCards land in GYM-42; here we demonstrate the shell
 * end-to-end with the shared primitives (StatCard grid + EmptyState) so the
 * structure, tokens, and reveal stagger are all exercisable now.
 */
import { StatCard, StatChip } from "@/components/ui/StatCard";
import { EmptyState } from "@/components/ui/EmptyState";

export function Dashboard() {
    return (
        <>
            <div className="grid grid-cols-2 gap-4">
                <StatCard value="—" label="Exercises" />
                <StatCard value="—" label="Sets" />
                <StatCard
                    value="—"
                    label="PRs"
                    accent
                    chip={<StatChip>PR</StatChip>}
                />
                <StatCard value="—" label="Streak" />
            </div>

            <EmptyState
                title="No trainings yet"
                subtitle="Log a workout in the bot and your activity will show up here."
            />
        </>
    );
}
