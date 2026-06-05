/**
 * The one history-row card (spec §11.2 / §11.5) — a <Card> composition, reused
 * for every day in the list. Bebas date heading (the hero), wrapping muscle
 * chips with a `+N` overflow, a Sora --hint counts line, and a trailing chevron.
 *
 * The WHOLE card is the tap target (≥44px): press scales 0.98 (§9.4) and a
 * light impact haptic fires before navigating to `/history/:date`. No per-card
 * edit/delete — the list is a pure browse surface (editing lives in the detail).
 */
import { useNavigate } from "react-router-dom";
import type { TrainingDay } from "@/api/training";
import { hapticImpact } from "@/telegram/webapp";
import { formatDayHeading } from "@/components/history/historyWindow";
import { Card } from "./Card";
import { Chip } from "./Chip";

/** How many muscle chips to show before collapsing the rest into `+N`. */
const MAX_CHIPS = 4;

export function DayCard({ day }: { day: TrainingDay }) {
    const navigate = useNavigate();

    const shown = day.muscles.slice(0, MAX_CHIPS);
    const overflow = day.muscles.length - shown.length;

    const exNoun = day.exercises_count === 1 ? "exercise" : "exercises";
    const setNoun = day.sets_count === 1 ? "set" : "sets";

    function open(): void {
        hapticImpact("light");
        navigate(`/history/${day.date}`);
    }

    return (
        <Card
            role="button"
            tabIndex={0}
            onClick={open}
            onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    open();
                }
            }}
            className="press-95 flex min-h-[44px] cursor-pointer items-center gap-4"
        >
            <div className="min-w-0 flex-1">
                <h2 className="tabular font-display text-title leading-none text-text">
                    {formatDayHeading(day.date)}
                </h2>

                {day.muscles.length > 0 ? (
                    /* GYM-77 #2: each chip wrapper has a max-width so a very
                       long muscle name clips with ellipsis, not unbounded. */
                    <div className="mt-2 flex flex-wrap gap-2">
                        {shown.map((m) => (
                            <span key={m} style={{ maxWidth: "10rem" }}>
                                <Chip title={m}>{m}</Chip>
                            </span>
                        ))}
                        {overflow > 0 ? <Chip>{`+${overflow}`}</Chip> : null}
                    </div>
                ) : null}

                <p className="tabular mt-2 text-label text-hint">
                    {day.exercises_count} {exNoun} · {day.sets_count} {setNoun}
                </p>
            </div>

            {/* Drill-in affordance. */}
            <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
                className="shrink-0"
            >
                <path
                    d="M9 6l6 6-6 6"
                    stroke="var(--hint)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </svg>
        </Card>
    );
}
