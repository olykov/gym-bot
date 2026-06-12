/**
 * StatCard primitive (spec §10.2) — big Bebas numeral (tabular-nums) over a
 * Sora --hint label. The `accent` flag makes a card the hero (e.g. PRs): the
 * numeral switches to --accent and an optional chip sits beside the label.
 * Reused for all four summary numbers in GYM-42. Count-up animation is left to
 * GYM-42 (it needs live data); this is the static, token-only primitive.
 *
 * GYM-123 #1: NOT tappable — no press state. Cards-as-entry-points (Sets →
 * History, Streak → explainer) was considered and deferred as feature creep.
 */
import type { ReactNode } from "react";
import { Card } from "./Card";

interface StatCardProps {
    value: ReactNode;
    label: string;
    accent?: boolean;
    /** Small marker beside the label (e.g. a PR chip on the hero card). */
    chip?: ReactNode;
}

export function StatCard({ value, label, accent = false, chip }: StatCardProps) {
    return (
        <Card>
            <div
                className={`tabular font-display text-stat leading-none ${
                    accent ? "text-accent" : "text-text"
                }`}
            >
                {value}
            </div>
            <div className="mt-1 flex items-center gap-2">
                <span className="text-label uppercase tracking-wide text-hint">
                    {label}
                </span>
                {chip}
            </div>
        </Card>
    );
}

interface StatChipProps {
    children: ReactNode;
    /** Optional extra classes (e.g. an appear animation from the caller). */
    className?: string;
}

/** The accent PR chip (spec §10.2 / §9.4). Subtle, --accent-weak fill.
 *
 * GYM-141: accepts an optional `className` so callers can attach a one-shot
 * appear animation (the SetRow PR chip) without coupling animation details
 * to this primitive.
 */
export function StatChip({ children, className }: StatChipProps) {
    return (
        <span
            className={`rounded-full bg-accent-weak px-2 py-[2px] text-label font-semibold uppercase text-accent${className ? ` ${className}` : ""}`}
        >
            {children}
        </span>
    );
}
