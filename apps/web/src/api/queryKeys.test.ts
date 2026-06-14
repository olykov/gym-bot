/**
 * Contract tests for the central query-key factory (GYM-126).
 *
 * These lock the EXACT key shapes that shipped before the factory existed —
 * cache behavior (and the prefix-invalidation contracts) must not change.
 * If a shape here needs editing, that is a cache-busting change: think twice.
 */
import { describe, expect, it } from "vitest";
import { DEVICE_TZ } from "@/lib/timezone";
import { queryKeys } from "./queryKeys";

const TZ = DEVICE_TZ ?? "UTC";

/** True when `key` starts with `prefix` (TanStack's invalidation match). */
function startsWith(
    key: readonly unknown[],
    prefix: readonly unknown[],
): boolean {
    return prefix.every((part, i) => key[i] === part);
}

describe("queryKeys — exact shapes", () => {
    it("muscle family", () => {
        expect(queryKeys.muscles.list).toEqual(["muscles"]);
        expect(queryKeys.muscles.exercises(7)).toEqual([
            "muscles",
            7,
            "exercises",
        ]);
        expect(queryKeys.muscles.hidden).toEqual(["muscles", "hidden"]);
    });

    it("exercise family", () => {
        expect(queryKeys.exercises.hidden("Chest")).toEqual([
            "exercises",
            "hidden",
            "Chest",
        ]);
        expect(queryKeys.exercises.search(7, "en", "bench", 8)).toEqual([
            "exercises",
            "search",
            7,
            "en",
            "bench",
            8,
        ]);
    });

    it("analytics family (tz suffix where the server groups by day)", () => {
        expect(queryKeys.analytics.summary()).toEqual([
            "analytics",
            "summary",
            TZ,
        ]);
        // GYM-136: week-compare carries the tz suffix like summary.
        expect(queryKeys.analytics.weekCompare()).toEqual([
            "analytics",
            "week-compare",
            TZ,
        ]);
        expect(queryKeys.analytics.activity("2026-01-01", "2026-06-30")).toEqual(
            ["analytics", "activity", "2026-01-01", "2026-06-30", TZ],
        );
        expect(queryKeys.analytics.topMuscles).toEqual([
            "analytics",
            "top-muscles",
        ]);
        expect(queryKeys.analytics.topExercises("Chest", 200)).toEqual([
            "analytics",
            "top-exercises",
            "Chest",
            200,
        ]);
        expect(
            queryKeys.analytics.exerciseProgress("Chest", "Bench Press"),
        ).toEqual(["analytics", "exercise-progress", "Chest", "Bench Press"]);
        expect(
            queryKeys.analytics.logContext("Chest", "Bench Press", "2026-06-12"),
        ).toEqual([
            "analytics",
            "log-context",
            "Chest",
            "Bench Press",
            "2026-06-12",
        ]);
        expect(
            queryKeys.analytics.exerciseTrend("Chest", "Bench Press", 8),
        ).toEqual(["analytics", "exercise-trend", "Chest", "Bench Press", 8]);
    });

    it("training family", () => {
        expect(queryKeys.training.days("2026-01-01", "2026-06-30")).toEqual([
            "training",
            "days",
            "2026-01-01",
            "2026-06-30",
            TZ,
        ]);
        // GYM-156: day key now carries the tz suffix so that server day-boundary
        // computation matches the list endpoint (both use the same local tz).
        expect(queryKeys.training.day("2026-06-12")).toEqual([
            "training",
            "day",
            "2026-06-12",
            TZ,
        ]);
    });
});

describe("queryKeys — prefix-invalidation contracts", () => {
    it("tz-suffixed keys are matched by their tz-less prefixes", () => {
        expect(
            startsWith(
                queryKeys.analytics.summary(),
                queryKeys.analytics.summaryPrefix,
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.activity("a", "b"),
                queryKeys.analytics.activityPrefix,
            ),
        ).toBe(true);
        // GYM-136: the tz-less prefix covers the tz-suffixed key …
        expect(
            startsWith(
                queryKeys.analytics.weekCompare(),
                queryKeys.analytics.weekComparePrefix,
            ),
        ).toBe(true);
        // … and must NOT collide with the summary family.
        expect(
            startsWith(
                queryKeys.analytics.summary(),
                queryKeys.analytics.weekComparePrefix,
            ),
        ).toBe(false);
        expect(
            startsWith(
                queryKeys.training.days("a", "b"),
                queryKeys.training.daysPrefix,
            ),
        ).toBe(true);
    });

    it("scoped prefixes cover their parameterized keys", () => {
        expect(
            startsWith(
                queryKeys.analytics.topExercises("Chest", 200),
                queryKeys.analytics.topExercisesPrefix("Chest"),
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.topExercises("Chest", 200),
                queryKeys.analytics.topExercisesPrefix(),
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.logContext("Chest", "Bench", "2026-06-12"),
                queryKeys.analytics.logContextPrefix("Chest", "Bench"),
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.logContext("Chest", "Bench", "2026-06-12"),
                queryKeys.analytics.logContextPrefix(),
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.exerciseProgress("Chest", "Bench"),
                queryKeys.analytics.exerciseProgressPrefix(),
            ),
        ).toBe(true);
        // GYM-135: the trend key is covered by both prefix forms (save path
        // uses the scoped one; history edits use the broad one).
        expect(
            startsWith(
                queryKeys.analytics.exerciseTrend("Chest", "Bench", 8),
                queryKeys.analytics.exerciseTrendPrefix("Chest", "Bench"),
            ),
        ).toBe(true);
        expect(
            startsWith(
                queryKeys.analytics.exerciseTrend("Chest", "Bench", 8),
                queryKeys.analytics.exerciseTrendPrefix(),
            ),
        ).toBe(true);
        // The trend prefix must NOT collide with exercise-progress keys.
        expect(
            startsWith(
                queryKeys.analytics.exerciseProgress("Chest", "Bench"),
                queryKeys.analytics.exerciseTrendPrefix(),
            ),
        ).toBe(false);
        expect(
            startsWith(
                queryKeys.exercises.hidden("Chest"),
                queryKeys.exercises.hiddenPrefix,
            ),
        ).toBe(true);
    });

    it("the bare muscles prefix fans out to the whole muscle family", () => {
        // ["muscles"] deliberately covers list + per-muscle exercises + hidden.
        expect(
            startsWith(queryKeys.muscles.exercises(7), queryKeys.muscles.list),
        ).toBe(true);
        expect(
            startsWith(queryKeys.muscles.hidden, queryKeys.muscles.list),
        ).toBe(true);
    });
});
