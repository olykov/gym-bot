/**
 * Progress route — placeholder shell content (GYM-41). The real muscle/exercise
 * pickers + ECharts progress chart land in GYM-42; here we show the loading
 * skeleton + empty path so the shell is demonstrable end-to-end.
 */
import { SkeletonChart } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export function Progress() {
    return (
        <>
            <SkeletonChart />
            <EmptyState
                title="Pick an exercise"
                subtitle="Choose a muscle and exercise to see your weight and reps over time."
            />
        </>
    );
}
