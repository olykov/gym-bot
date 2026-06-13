/**
 * Unit tests for the set-logger pure derivations (GYM-124).
 * These encode the invariants behind GYM-74 (server w×r recap), GYM-104
 * (derived effective PR, race-free) and GYM-130 (ASC ghost comparison +
 * weight-first/reps-tiebreak deltas — reverting the GYM-101 DESC order).
 */
import { describe, expect, it } from "vitest";
import type { TrainingSet } from "@/api/training";
import type { LogSet, PersonalRecord } from "@/api/analytics";
import { ApiError } from "@/api/client";
import {
    beatsLastSession,
    buildComparisonRows,
    computeDelta,
    computeEffectivePR,
    computeNextSet,
    derivePrefill,
    findNextGhostSet,
    mergeRecap,
    resolvePrBeat,
    saveErrorMessage,
    summarizeSession,
    type SessionLogEntry,
    type SessionSet,
} from "./derive";

function srv(set: number, weight: number, reps: number): TrainingSet {
    // GYM-141: is_pr defaults false in test fixtures; tests that care set it explicitly.
    return { training_id: `t-${set}`, set, weight, reps, is_pr: false };
}

function ses(set: number, weight: number, reps: number): SessionSet {
    return { set, weight, reps };
}

function ghost(set: number, weight: number, reps: number): LogSet {
    return { set, weight, reps };
}

const PR80: PersonalRecord = { weight: 80, reps: 5, date: "2026-05-01T10:00:00Z" };

describe("computeNextSet", () => {
    it("returns 1 when nothing is logged", () => {
        expect(computeNextSet([], [])).toBe(1);
    });

    it("is max-based over completed sets, not a count", () => {
        expect(computeNextSet([1, 2, 3], [])).toBe(4);
        // A gap must not re-issue a taken number.
        expect(computeNextSet([1, 3], [])).toBe(4);
    });

    it("considers session sets alone", () => {
        expect(computeNextSet([], [ses(2, 50, 8)])).toBe(3);
    });

    it("takes the max across the completed ∪ session union", () => {
        expect(computeNextSet([2], [ses(5, 50, 8)])).toBe(6);
        expect(computeNextSet([7], [ses(3, 50, 8)])).toBe(8);
    });
});

describe("derivePrefill (GYM-152 — last-training-set-N is primary)", () => {
    // (a) Primary: after a session set exists, set N+1 uses last_session_sets[N+1]
    //     — NOT a repeat of the session's last set.
    it("(a) set N+1 prefills last_session_sets[N+1], not the session's last set", () => {
        const sessionSets = [ses(1, 50, 10)]; // just logged set 1 at 50×10
        const lastSessionSets = [
            ghost(1, 48, 10), // last time set 1
            ghost(2, 52, 8),  // last time set 2 — should be the prefill
        ];
        // nextSet = 2; last_session_sets has an entry for set 2 → use it.
        expect(derivePrefill(2, sessionSets, lastSessionSets)).toEqual({
            weight: 52,
            reps: 8,
        });
    });

    it("(a) also applies when there are multiple session sets already", () => {
        const sessionSets = [ses(1, 60, 8), ses(2, 62, 7)];
        const lastSessionSets = [
            ghost(1, 58, 8),
            ghost(2, 60, 7),
            ghost(3, 55, 10), // last time set 3
        ];
        expect(derivePrefill(3, sessionSets, lastSessionSets)).toEqual({
            weight: 55,
            reps: 10,
        });
    });

    // (b) Fallback: when last_session_sets has no entry for nextSet, repeat
    //     this session's last set.
    it("(b) falls back to repeating this session's last set when last_session_sets has no entry for nextSet", () => {
        const sessionSets = [ses(1, 50, 10), ses(2, 50, 10)];
        const lastSessionSets = [ghost(1, 48, 10)]; // only one set last time
        // nextSet = 3; no ghost for set 3 → repeat session's last (set 2).
        expect(derivePrefill(3, sessionSets, lastSessionSets)).toEqual({
            weight: 50,
            reps: 10,
        });
    });

    it("(b) fallback also applies when last_session_sets is empty but a session set exists", () => {
        const sessionSets = [ses(1, 70, 5)];
        expect(derivePrefill(2, sessionSets, [])).toEqual({
            weight: 70,
            reps: 5,
        });
    });

    // (c) New exercise / empty last_session → empty (both null).
    it("(c) new exercise with no session sets and no last_session_sets → empty", () => {
        expect(derivePrefill(1, [], [])).toEqual({
            weight: null,
            reps: null,
        });
    });

    it("(c) first set with no last_session entry and no session sets yet → empty", () => {
        // last_session_sets exists but has no entry for set 1 and session is empty.
        expect(derivePrefill(1, [], [ghost(2, 50, 8)])).toEqual({
            weight: null,
            reps: null,
        });
    });

    // (d) Never-overwrite guard — derivePrefill itself does not read the current
    //     text values (the guard lives in the useEffect), but we verify that
    //     primary wins over fallback unconditionally (the "only fill empty"
    //     responsibility sits in SetLogger.tsx and is tested conceptually here
    //     by confirming derivePrefill always returns the primary source).
    it("(d) primary source (last_session set N) wins even when session sets exist", () => {
        // Session has set 1 = 100×8; last_session has set 2 = 90×6.
        // derivePrefill must return the last_session value, not the session repeat.
        const sessionSets = [ses(1, 100, 8)];
        const lastSessionSets = [ghost(1, 95, 8), ghost(2, 90, 6)];
        const result = derivePrefill(2, sessionSets, lastSessionSets);
        // Must be last_session's set 2, NOT session's last set (100×8).
        expect(result).toEqual({ weight: 90, reps: 6 });
        expect(result.weight).not.toBe(100);
        expect(result.reps).not.toBe(8);
    });
});

describe("mergeRecap", () => {
    it("returns an empty list when no source has sets", () => {
        expect(mergeRecap([], [], [])).toEqual([]);
    });

    it("sorts rows ASC so the comparison reads top-down (GYM-130, reverts GYM-101 DESC)", () => {
        const rows = mergeRecap([1, 2], [], [ses(3, 60, 8)]);
        expect(rows.map((r) => r.set)).toEqual([1, 2, 3]);
    });

    it("shows ✓-only rows (null w×r) for log-context-only set numbers", () => {
        const rows = mergeRecap([1], [], []);
        expect(rows).toEqual([{ set: 1, weight: null, reps: null }]);
    });

    it("fills w×r from server sets for pre-session sets (GYM-74)", () => {
        const rows = mergeRecap([1], [srv(1, 55, 10)], []);
        expect(rows).toEqual([{ set: 1, weight: 55, reps: 10 }]);
    });

    it("prefers the session value over the server value for the same set", () => {
        const rows = mergeRecap([], [srv(1, 55, 10)], [ses(1, 60, 8)]);
        expect(rows).toEqual([{ set: 1, weight: 60, reps: 8 }]);
    });

    it("unions all three sources without duplicating set numbers", () => {
        const rows = mergeRecap(
            [1, 2],
            [srv(2, 50, 10)],
            [ses(3, 60, 8)],
        );
        expect(rows).toEqual([
            { set: 1, weight: null, reps: null },
            { set: 2, weight: 50, reps: 10 },
            { set: 3, weight: 60, reps: 8 },
        ]);
    });
});

describe("computeDelta (GYM-130 — weight first, reps tiebreak; LOCKED)", () => {
    it("more weight → up by weight (reps ignored, even when fewer)", () => {
        expect(
            computeDelta({ weight: 102.5, reps: 8 }, { weight: 100, reps: 8 }),
        ).toEqual({ kind: "up", metric: "weight", amount: 2.5 });
        // Weight wins the comparison even when today's reps DROPPED.
        expect(
            computeDelta({ weight: 102.5, reps: 5 }, { weight: 100, reps: 10 }),
        ).toEqual({ kind: "up", metric: "weight", amount: 2.5 });
    });

    it("less weight → down by weight (reps ignored, even when more)", () => {
        expect(
            computeDelta({ weight: 97.5, reps: 12 }, { weight: 100, reps: 8 }),
        ).toEqual({ kind: "down", metric: "weight", amount: 2.5 });
    });

    it("equal weight, more reps → up by reps (the tiebreak)", () => {
        expect(
            computeDelta({ weight: 100, reps: 9 }, { weight: 100, reps: 8 }),
        ).toEqual({ kind: "up", metric: "reps", amount: 1 });
    });

    it("equal weight, fewer reps → down by reps", () => {
        expect(
            computeDelta({ weight: 100, reps: 6 }, { weight: 100, reps: 8 }),
        ).toEqual({ kind: "down", metric: "reps", amount: 2 });
    });

    it("equal weight and reps → eq", () => {
        expect(
            computeDelta({ weight: 100, reps: 8 }, { weight: 100, reps: 8 }),
        ).toEqual({ kind: "eq" });
    });
});

describe("buildComparisonRows (GYM-130 — TODAY | LAST TIME by set number)", () => {
    it("returns an empty list when no source has sets", () => {
        expect(buildComparisonRows([], [], [], [])).toEqual([]);
    });

    it("unions today and last-session set numbers, ASC", () => {
        const rows = buildComparisonRows(
            [],
            [],
            [ses(2, 102.5, 8)],
            [ghost(1, 100, 8), ghost(3, 100, 7)],
        );
        expect(rows.map((r) => r.set)).toEqual([1, 2, 3]);
    });

    it("produces ghost rows (today null) for last-session-only sets", () => {
        const rows = buildComparisonRows([], [], [], [ghost(1, 100, 7)]);
        expect(rows).toEqual([
            {
                set: 1,
                today: null,
                last: { weight: 100, reps: 7 },
                delta: null,
            },
        ]);
    });

    it("computes the delta only when both sides carry full w×r", () => {
        const rows = buildComparisonRows(
            [1, 2],
            [srv(2, 100, 9)],
            [],
            [ghost(1, 100, 8), ghost(2, 100, 8)],
        );
        // Set 1 is ✓-only today (no w×r) → figure stays honest, no delta.
        expect(rows[0]).toEqual({
            set: 1,
            today: { set: 1, weight: null, reps: null },
            last: { weight: 100, reps: 8 },
            delta: null,
        });
        // Set 2 has a server figure → reps-tiebreak delta.
        expect(rows[1]).toEqual({
            set: 2,
            today: { set: 2, weight: 100, reps: 9 },
            last: { weight: 100, reps: 8 },
            delta: { kind: "up", metric: "reps", amount: 1 },
        });
    });

    it("keeps the today priority session > server (GYM-74 invariant)", () => {
        const rows = buildComparisonRows(
            [],
            [srv(1, 55, 10)],
            [ses(1, 60, 8)],
            [ghost(1, 57.5, 8)],
        );
        expect(rows[0]?.today).toEqual({ set: 1, weight: 60, reps: 8 });
        expect(rows[0]?.delta).toEqual({
            kind: "up",
            metric: "weight",
            amount: 2.5,
        });
    });

    it("no prior session → today-only rows with last/delta null (single-column passthrough)", () => {
        const rows = buildComparisonRows([], [], [ses(1, 60, 8)], []);
        expect(rows).toEqual([
            {
                set: 1,
                today: { set: 1, weight: 60, reps: 8 },
                last: null,
                delta: null,
            },
        ]);
    });

    it("today-only extra sets (beyond the ghost) get last/delta null", () => {
        const rows = buildComparisonRows(
            [],
            [],
            [ses(1, 100, 8), ses(2, 100, 8)],
            [ghost(1, 100, 8)],
        );
        expect(rows[1]).toEqual({
            set: 2,
            today: { set: 2, weight: 100, reps: 8 },
            last: null,
            delta: null,
        });
    });
});

describe("findNextGhostSet (GYM-130 — the standing target)", () => {
    it("returns the first last-session set with no today entry", () => {
        const rows = buildComparisonRows(
            [],
            [],
            [ses(1, 100, 8)],
            [ghost(1, 100, 8), ghost(2, 100, 8), ghost(3, 100, 7)],
        );
        expect(findNextGhostSet(rows)).toBe(2);
    });

    it("returns null when every ghost is matched or there is no ghost", () => {
        const matched = buildComparisonRows(
            [],
            [],
            [ses(1, 100, 8)],
            [ghost(1, 100, 8)],
        );
        expect(findNextGhostSet(matched)).toBeNull();
        const noGhost = buildComparisonRows([], [], [ses(1, 100, 8)], []);
        expect(findNextGhostSet(noGhost)).toBeNull();
    });

    it("treats a ✓-only today entry as logged (not a ghost target)", () => {
        const rows = buildComparisonRows(
            [1],
            [],
            [],
            [ghost(1, 100, 8), ghost(2, 100, 8)],
        );
        expect(findNextGhostSet(rows)).toBe(2);
    });
});

describe("computeEffectivePR", () => {
    it("returns null when there is no server PR and no session sets", () => {
        expect(computeEffectivePR(null, [])).toBeNull();
    });

    it("returns the server PR (with reps) when it is the only source", () => {
        expect(computeEffectivePR(PR80, [])).toEqual({ weight: 80, reps: 5 });
    });

    it("returns the best session weight (no reps) when ctx has no PR", () => {
        expect(
            computeEffectivePR(null, [ses(1, 40, 8), ses(2, 45, 6)]),
        ).toEqual({ weight: 45, reps: null });
    });

    it("keeps the server PR and its reps when it beats every session set", () => {
        expect(computeEffectivePR(PR80, [ses(1, 60, 8)])).toEqual({
            weight: 80,
            reps: 5,
        });
    });

    it("keeps the server reps on an exact tie (server is the source)", () => {
        expect(computeEffectivePR(PR80, [ses(1, 80, 3)])).toEqual({
            weight: 80,
            reps: 5,
        });
    });

    it("drops reps when a session set strictly exceeds the server PR", () => {
        expect(computeEffectivePR(PR80, [ses(1, 82.5, 2)])).toEqual({
            weight: 82.5,
            reps: null,
        });
    });

    it("GYM-104 race: a session set saved before ctx resolves never hides a higher server PR", () => {
        const earlySession = [ses(1, 2.5, 10)];
        // Before log-context resolves the chip can only know the session best…
        expect(computeEffectivePR(null, earlySession)).toEqual({
            weight: 2.5,
            reps: null,
        });
        // …and once the server PR (80kg) arrives, it wins — no lock-in at 2.5.
        expect(computeEffectivePR(PR80, earlySession)).toEqual({
            weight: 80,
            reps: 5,
        });
    });
});

describe("beatsLastSession (GYM-131/132 — beat-last at save time)", () => {
    const ghosts = [ghost(1, 100, 8), ghost(2, 100, 7)];

    it("returns false when no ghost matches the set number (nothing to beat)", () => {
        expect(beatsLastSession([], ses(1, 200, 10))).toBe(false);
        expect(beatsLastSession(ghosts, ses(3, 200, 10))).toBe(false);
    });

    it("more weight than the same-number ghost → true", () => {
        expect(beatsLastSession(ghosts, ses(1, 102.5, 5))).toBe(true);
    });

    it("equal weight, more reps (the LOCKED tiebreak) → true", () => {
        expect(beatsLastSession(ghosts, ses(2, 100, 8))).toBe(true);
    });

    it("equal set → false; lower weight → false", () => {
        expect(beatsLastSession(ghosts, ses(1, 100, 8))).toBe(false);
        expect(beatsLastSession(ghosts, ses(1, 97.5, 12))).toBe(false);
    });
});

describe("summarizeSession (GYM-132 — all client-side, zero network)", () => {
    function entry(
        muscle: string,
        exercise: string,
        set: number,
        weight: number,
        reps: number,
        flags?: { beatLast?: boolean; beatPR?: boolean },
    ): SessionLogEntry {
        return {
            muscle,
            exercise,
            set,
            weight,
            reps,
            beatLast: flags?.beatLast ?? false,
            beatPR: flags?.beatPR ?? false,
        };
    }

    it("an empty log yields all zeros", () => {
        expect(summarizeSession([])).toEqual({
            sets: 0,
            exercises: 0,
            volume: 0,
            beatLast: 0,
            prs: 0,
        });
    });

    it("counts sets, distinct exercises and Σ weight×reps volume", () => {
        const log = [
            entry("Chest", "Bench Press", 1, 100, 8),
            entry("Chest", "Bench Press", 2, 102.5, 8),
            entry("Back", "Row", 1, 60, 10),
        ];
        expect(summarizeSession(log)).toEqual({
            sets: 3,
            exercises: 2,
            volume: 100 * 8 + 102.5 * 8 + 60 * 10, // 2220
            beatLast: 0,
            prs: 0,
        });
    });

    it("a same-named exercise under another muscle is a DISTINCT exercise", () => {
        const log = [
            entry("Chest", "Press", 1, 50, 8),
            entry("Shoulders", "Press", 1, 30, 8),
        ];
        expect(summarizeSession(log).exercises).toBe(2);
    });

    it("counts beat-last sets and PR beats independently", () => {
        const log = [
            entry("Chest", "Bench Press", 1, 100, 8, { beatLast: true }),
            entry("Chest", "Bench Press", 2, 105, 6, {
                beatLast: true,
                beatPR: true,
            }),
            entry("Chest", "Bench Press", 3, 95, 8),
        ];
        const summary = summarizeSession(log);
        expect(summary.beatLast).toBe(2);
        expect(summary.prs).toBe(1);
    });

    it("keeps half-kilo volume exact (×2.5kg plates)", () => {
        expect(summarizeSession([entry("Legs", "Squat", 1, 102.5, 3)]).volume).toBe(
            307.5,
        );
    });
});

describe("resolvePrBeat (GYM-133 — one PR kind per save, weight > reps-at-weight > e1rm)", () => {
    it("first set ever (no PR source at all) → weight (the pre-GYM-133 behavior)", () => {
        expect(resolvePrBeat(null, [], [], ses(1, 60, 8))).toBe("weight");
    });

    it("strictly above the server PR weight → weight", () => {
        expect(resolvePrBeat(PR80, [], [], ses(1, 82.5, 1))).toBe("weight");
    });

    it("strictly above the best SESSION weight (no server PR) → weight", () => {
        expect(resolvePrBeat(null, [], [ses(1, 50, 8)], ses(2, 52.5, 8))).toBe(
            "weight",
        );
    });

    it("GYM-104 race preserved: a higher server PR suppresses the weight kind", () => {
        // Session best is 2.5kg, but the resolved server PR is 80kg — saving
        // 50kg must NOT be a weight PR (and beats nothing else known).
        expect(resolvePrBeat(PR80, [], [ses(1, 2.5, 10)], ses(2, 50, 10))).toBe(
            null,
        );
    });

    it("hierarchy: a weight PR also beats the e1RM, but only 'weight' fires", () => {
        // 85×8 beats both PR80's weight and its e1RM (80×5 → 93.33).
        expect(resolvePrBeat(PR80, [], [], ses(1, 85, 8))).toBe("weight");
    });

    it("same weight as the PR, more reps → reps-at-weight (quiet)", () => {
        // PR80 is 80×5 — 80×7 is not a weight PR but beats the reps at 80.
        expect(resolvePrBeat(PR80, [], [], ses(1, 80, 7))).toBe(
            "reps-at-weight",
        );
    });

    it("same weight as a LAST-SESSION set, more reps → reps-at-weight", () => {
        const last = [ghost(1, 70, 8)];
        expect(resolvePrBeat(PR80, last, [], ses(1, 70, 9))).toBe(
            "reps-at-weight",
        );
    });

    it("same weight as an earlier SESSION set, more reps → reps-at-weight", () => {
        expect(
            resolvePrBeat(null, [], [ses(1, 50, 8)], ses(2, 50, 10)),
        ).toBe("reps-at-weight");
    });

    it("reps TIE at a known weight → not a reps PR (strict >), and no e1RM gain → null", () => {
        expect(resolvePrBeat(PR80, [], [], ses(1, 80, 5))).toBe(null);
    });

    it("best-known reps at the weight is the MAX across the pool", () => {
        // 70kg appears at 8 reps (last session) and 10 reps (this session):
        // 9 reps does NOT beat the best known (10).
        const last = [ghost(1, 70, 8)];
        expect(
            resolvePrBeat(PR80, last, [ses(1, 70, 10)], ses(2, 70, 9)),
        ).toBe(null);
    });

    it("lower weight, enough reps to beat the best-known e1RM → e1rm (quiet)", () => {
        // PR80 = 80×5 → e1RM 93.33. 75×9 → 97.5 beats it at a NOVEL weight
        // (75 was never lifted, so reps-at-weight can't apply).
        expect(resolvePrBeat(PR80, [], [], ses(1, 75, 9))).toBe("e1rm");
    });

    it("e1RM compares against the whole pool, not just the PR", () => {
        // Last session has 70×20 → e1RM 116.67, well above PR80's 93.33:
        // 75×9 → 97.5 beats the PR-derived e1RM but NOT the pool max.
        const last = [ghost(1, 70, 20)];
        expect(resolvePrBeat(PR80, last, [], ses(1, 75, 9))).toBe(null);
    });

    it("e1RM tie → null (strict >)", () => {
        // PR 100×6 → e1RM 120; 90×10 → exactly 120 as well (novel weight,
        // below the PR, so neither higher kind applies).
        const pr = { weight: 100, reps: 6, date: "2026-05-01T10:00:00Z" };
        expect(resolvePrBeat(pr, [], [], ses(1, 90, 10))).toBe(null);
    });

    it("nothing beaten (below PR, novel weight, lower e1RM) → null", () => {
        expect(resolvePrBeat(PR80, [], [], ses(1, 60, 5))).toBe(null);
    });

    it("hierarchy: reps-at-weight wins over e1rm when both apply", () => {
        // 80×7 beats the reps at 80 AND the pool e1RM (93.33 → 98.67), but
        // only the higher kind fires.
        expect(resolvePrBeat(PR80, [], [], ses(1, 80, 7))).toBe(
            "reps-at-weight",
        );
    });
});

describe("saveErrorMessage (GYM-125 #2)", () => {
    it("names the colliding set on a 409 (set-number collision, §12.8)", () => {
        const err = new ApiError(409, "Set already exists");
        expect(saveErrorMessage(err, 3, "en")).toBe(
            "Set 3 already exists — refreshed your numbers.",
        );
    });

    it("keeps the generic message for any other ApiError status", () => {
        expect(saveErrorMessage(new ApiError(500, "boom"), 3, "en")).toBe(
            "Couldn't save that set — try again.",
        );
        expect(
            saveErrorMessage(new ApiError(0, "Network request failed"), 1, "en"),
        ).toBe("Couldn't save that set — try again.");
    });

    it("keeps the generic message for non-ApiError values", () => {
        expect(saveErrorMessage(new Error("plain"), 2, "en")).toBe(
            "Couldn't save that set — try again.",
        );
        expect(saveErrorMessage(undefined, 2, "en")).toBe(
            "Couldn't save that set — try again.",
        );
    });

    it("localizes via the catalog for ru (GYM-109)", () => {
        const err = new ApiError(409, "Set already exists");
        expect(saveErrorMessage(err, 3, "ru")).toBe(
            "Сет 3 уже записан — мы обновили номера.",
        );
        expect(saveErrorMessage(undefined, 2, "ru")).toBe(
            "Не удалось сохранить сет — попробуйте ещё раз.",
        );
    });
});
