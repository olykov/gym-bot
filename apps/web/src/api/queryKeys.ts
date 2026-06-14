/**
 * Central typed query-key factory (GYM-126) — the ONE place every TanStack
 * Query key is built. Hooks (useAnalytics / useTraining / useRecord) and every
 * invalidation call site import from here, so a cache hit and its invalidation
 * can never drift apart by a hand-typed string.
 *
 * Two kinds of exports per family:
 *  - key builders (functions / consts) — the EXACT key a query is stored
 *    under; shapes are frozen (`as const`) and covered by queryKeys.test.ts.
 *  - `*Prefix` consts — the documented invalidation contracts. TanStack
 *    matches by array prefix, so invalidating a prefix hits every key that
 *    starts with it. Each prefix below states exactly which keys it covers.
 *
 * Timezone suffixes: `summary`, `activity`, `training.days` and `training.day`
 * carry the resolved device timezone (DEVICE_TZ ?? "UTC") as their LAST
 * element so a tz change across reloads is a cache miss. Their invalidation
 * contracts deliberately use the tz-LESS prefix — `["analytics","summary"]`
 * invalidates the summary for whatever tz is cached. This was previously an
 * unwritten coincidence of string prefixes; it is now the documented contract.
 */
import { DEVICE_TZ } from "@/lib/timezone";

/** The tz suffix shared by summary/activity/days keys (server day grouping). */
const TZ = DEVICE_TZ ?? "UTC";

export const queryKeys = {
    muscles: {
        /**
         * `GET /muscles` — the visible muscle catalog.
         *
         * ALSO the broadest muscle-family invalidation prefix: invalidating
         * `["muscles"]` covers `list`, every `exercises(muscleId)` and
         * `hidden` (all start with "muscles"). Every catalog mutation
         * (create/rename/delete/hide/unhide) relies on this fan-out.
         */
        list: ["muscles"] as const,
        /** `GET /muscles/{id}/exercises` — full catalog under one muscle. */
        exercises: (muscleId: number | null) =>
            ["muscles", muscleId, "exercises"] as const,
        /** `GET /muscles/hidden` — hidden global muscles (GYM-103). */
        hidden: ["muscles", "hidden"] as const,
    },

    exercises: {
        /** `GET /exercises/hidden?muscle=<name>` — hidden per muscle (GYM-103). */
        hidden: (muscleName: string | null) =>
            ["exercises", "hidden", muscleName] as const,
        /**
         * Invalidation prefix for ALL hidden-exercise caches (every muscle).
         * Used after hide/unhide/move so the "Show Hidden" expander updates
         * immediately for any muscle (GYM-104 #2).
         */
        hiddenPrefix: ["exercises", "hidden"] as const,
        /** `GET /exercises/search` — ranked candidates (GYM-94). */
        search: (
            muscleId: number | null,
            lang: string,
            q: string,
            limit: number,
        ) => ["exercises", "search", muscleId, lang, q, limit] as const,
    },

    analytics: {
        /**
         * `GET /analytics/summary` — dashboard numbers. Carries the tz suffix;
         * invalidated by `summaryPrefix` (tz-less, see module doc).
         */
        summary: () => ["analytics", "summary", TZ] as const,
        /** Invalidation prefix for `summary()` — matches any tz suffix. */
        summaryPrefix: ["analytics", "summary"] as const,
        /**
         * `GET /analytics/week-compare` — this-week vs last-week totals
         * (GYM-136). Carries the tz suffix (server-side week grouping);
         * invalidated by `weekComparePrefix` (tz-less, see module doc).
         */
        weekCompare: () => ["analytics", "week-compare", TZ] as const,
        /** Invalidation prefix for `weekCompare()` — matches any tz suffix. */
        weekComparePrefix: ["analytics", "week-compare"] as const,
        /**
         * `GET /analytics/activity` — grid window. Carries the tz suffix;
         * invalidated by `activityPrefix` (tz-less AND window-less: a new set
         * must refresh every cached window).
         */
        activity: (from: string, to: string) =>
            ["analytics", "activity", from, to, TZ] as const,
        /** Invalidation prefix for `activity(...)` — all windows, any tz. */
        activityPrefix: ["analytics", "activity"] as const,
        /** `GET /analytics/top-muscles` — frequency-ranked muscles. */
        topMuscles: ["analytics", "top-muscles"] as const,
        /** `GET /analytics/top-exercises` — frequency-ranked, per muscle. */
        topExercises: (muscle: string | null, limit: number) =>
            ["analytics", "top-exercises", muscle, limit] as const,
        /**
         * Invalidation prefix for `topExercises(...)`: pass a muscle to hit
         * that muscle's ranking regardless of `limit`; omit it to hit ALL
         * muscles (rename/move/unhide fan-out).
         */
        topExercisesPrefix: (muscle?: string) =>
            muscle === undefined
                ? (["analytics", "top-exercises"] as const)
                : (["analytics", "top-exercises", muscle] as const),
        /** `GET /analytics/exercise-progress` — per-set series (Progress). */
        exerciseProgress: (muscle: string | null, exercise: string | null) =>
            ["analytics", "exercise-progress", muscle, exercise] as const,
        /**
         * Invalidation prefix for `exerciseProgress(...)`: with both names it
         * is the exact key; omit both to hit EVERY series (an edit/delete/
         * rename can move any per-exercise PR — GYM-105).
         */
        exerciseProgressPrefix: (muscle?: string, exercise?: string) =>
            muscle !== undefined && exercise !== undefined
                ? (["analytics", "exercise-progress", muscle, exercise] as const)
                : (["analytics", "exercise-progress"] as const),
        /**
         * `GET /analytics/exercise-trend` — session volume delta + per-session
         * max-e1RM series over a trailing window (GYM-134). `weeks` is part of
         * the key so different windows cache independently.
         */
        exerciseTrend: (
            muscle: string | null,
            exercise: string | null,
            weeks: number,
        ) => ["analytics", "exercise-trend", muscle, exercise, weeks] as const,
        /**
         * Invalidation prefix for `exerciseTrend(...)`: with both names it
         * covers every window for one exercise (the save path); with no names
         * it covers EVERY exercise (history edit/delete — a weight edit moves
         * the e1RM history, GYM-135).
         */
        exerciseTrendPrefix: (muscle?: string, exercise?: string) =>
            muscle !== undefined && exercise !== undefined
                ? (["analytics", "exercise-trend", muscle, exercise] as const)
                : (["analytics", "exercise-trend"] as const),
        /**
         * `GET /analytics/log-context` — the single Phase-B read (GYM-71):
         * completed set numbers + last session sets + PR for one exercise on
         * one date.
         */
        logContext: (
            muscle: string | null,
            exercise: string | null,
            date: string,
        ) => ["analytics", "log-context", muscle, exercise, date] as const,
        /**
         * Invalidation prefix for `logContext(...)`: with names it covers all
         * DATES for one exercise (save / add→resolve paths); with no names it
         * covers EVERY exercise (history edit/delete — GYM-105: the SetLogger
         * must never show deleted sets as done).
         */
        logContextPrefix: (muscle?: string, exercise?: string) =>
            muscle !== undefined && exercise !== undefined
                ? (["analytics", "log-context", muscle, exercise] as const)
                : (["analytics", "log-context"] as const),
    },

    training: {
        /**
         * `GET /training/days` — one day-list window (§11.2). Carries the tz
         * suffix (server-side day grouping); invalidated by `daysPrefix`.
         */
        days: (from: string, to: string) =>
            ["training", "days", from, to, TZ] as const,
        /** Invalidation prefix for `days(...)` — all windows, any tz. */
        daysPrefix: ["training", "days"] as const,
        /**
         * `GET /training/day/{date}` — one day's grouped detail (§11.3).
         * Carries the tz suffix (GYM-156: server day-boundary uses local tz,
         * must match the list). Invalidated by the exact key (no prefix needed
         * — callers pass the date directly).
         */
        day: (date: string) => ["training", "day", date, TZ] as const,
    },
} as const;
