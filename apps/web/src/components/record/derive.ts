/**
 * Pure derivations for the set-logger (spec §12.3) — no React, no DOM.
 *
 * Extracted from SetLogger.tsx (GYM-124) so the regression-prone logic that
 * already produced real bugs (GYM-101 ordering, GYM-104 PR race) is unit-
 * testable in isolation. SetLogger.tsx calls these from useMemo and stays a
 * thin view; the algorithms and their invariants live here.
 */
import type { TrainingSet } from "@/api/training";
import type { LogSet, PersonalRecord } from "@/api/analytics";
import { ApiError } from "@/api/client";
import type { Locale } from "@/i18n/locales";
import { getLocale } from "@/i18n/locale";
import { translate } from "@/i18n/catalog";
import { epley } from "@/lib/e1rm";

/** A set logged in THIS session (full weight/reps, always exact). */
export interface SessionSet {
    set: number;
    weight: number;
    reps: number;
}

/** One recap row: null weight/reps means "set number known only" (renders ✓). */
export interface RecapRow {
    set: number;
    weight: number | null;
    reps: number | null;
}

/** The PR the chip shows: reps is null when a session set is the source. */
export interface EffectivePR {
    weight: number;
    reps: number | null;
}

/**
 * Auto set # = max(completed ∪ session) + 1 (§12.3, never a naive counter).
 *
 * @param completed - set numbers already logged today (log-context).
 * @param sessionSets - sets saved in THIS session for this exercise.
 */
export function computeNextSet(
    completed: number[],
    sessionSets: SessionSet[],
): number {
    const all = [...completed, ...sessionSets.map((s) => s.set)];
    return (all.length ? Math.max(...all) : 0) + 1;
}

/**
 * Recap rows: union of all set numbers known today, with w×r sourced in
 * priority:
 *  1. This-session set (always exact, was just logged).
 *  2. serverSets from GET /training/day/{today} (carries weight+reps from
 *     the server) — fixes the reopen/Continue ✓-only display (GYM-74).
 *  3. completed_sets from log-context (set numbers only, no w×r → shows ✓).
 *
 * GYM-130: rows are sorted ASC (Set 1 first) — the ghost comparison reads
 * line-by-line top-down, reverting the GYM-101 DESC ordering. "Last set
 * visible" is now solved by auto-scrolling the recap region after a save.
 *
 * @param completedSets - set numbers from log-context `completed_sets`.
 * @param serverSets - today's sets from `GET /training/day/{today}`.
 * @param sessionSets - sets saved in THIS session.
 */
export function mergeRecap(
    completedSets: number[],
    serverSets: TrainingSet[],
    sessionSets: SessionSet[],
): RecapRow[] {
    const sessionByNum = new Map(sessionSets.map((s) => [s.set, s]));
    const serverByNum = new Map(serverSets.map((s) => [s.set, s]));
    const nums = new Set<number>([
        ...completedSets,
        ...serverSets.map((s) => s.set),
        ...sessionSets.map((s) => s.set),
    ]);
    return [...nums]
        .sort((a, b) => a - b)
        .map((n) => {
            const session = sessionByNum.get(n) ?? null;
            // Server set provides w×r for pre-session sets (reopen / Continue).
            const srv = serverByNum.get(n);
            return {
                set: n,
                weight: session?.weight ?? srv?.weight ?? null,
                reps: session?.reps ?? srv?.reps ?? null,
            };
        });
}

/** A fully-known weight×reps pair (both values present). */
export interface FigurePair {
    weight: number;
    reps: number;
}

/**
 * GYM-130: per-set delta vs the last session — a discriminated union.
 * `eq` carries no metric/amount (nothing moved on either axis).
 */
export type Delta =
    | { kind: "up"; metric: "weight" | "reps"; amount: number }
    | { kind: "down"; metric: "weight" | "reps"; amount: number }
    | { kind: "eq" };

/**
 * One row of the GYM-130 comparison recap (TODAY | LAST TIME), matched by
 * set number:
 *  - `today` — null when the set exists only in last session (a GHOST row);
 *    `{weight: null, reps: null}` when only the set NUMBER is known today
 *    (the honest `— · —` figure, GYM-123 #3).
 *  - `last` — the matching last-session set, or null when today-only.
 *  - `delta` — computed ONLY when both sides carry full weight+reps.
 */
export interface ComparisonRow {
    set: number;
    today: RecapRow | null;
    last: FigurePair | null;
    delta: Delta | null;
}

/**
 * GYM-130 delta rule (operator decision #2, LOCKED): compare WEIGHT first;
 * reps only break the tie when the weights are equal.
 *
 *  - today.weight > last.weight → up   {+x kg}
 *  - today.weight < last.weight → down {−x kg}
 *  - weights equal, more reps   → up   {+n reps}
 *  - weights equal, fewer reps  → down {−n reps}
 *  - both equal                 → eq ("=")
 */
export function computeDelta(today: FigurePair, last: FigurePair): Delta {
    if (today.weight > last.weight) {
        return { kind: "up", metric: "weight", amount: today.weight - last.weight };
    }
    if (today.weight < last.weight) {
        return { kind: "down", metric: "weight", amount: last.weight - today.weight };
    }
    if (today.reps > last.reps) {
        return { kind: "up", metric: "reps", amount: today.reps - last.reps };
    }
    if (today.reps < last.reps) {
        return { kind: "down", metric: "reps", amount: last.reps - today.reps };
    }
    return { kind: "eq" };
}

/**
 * GYM-130: the ghost-comparison rows — TODAY vs LAST TIME matched by set
 * number, ASC (Set 1 first; the comparison reads top-down).
 *
 * Row set = union(today's set numbers, last_session_sets numbers). The today
 * column reuses {@link mergeRecap} (priority session > server > ✓-only is
 * preserved verbatim); last-session-only numbers become ghost rows
 * (`today: null`). With no prior session every row has `last: null` and
 * `delta: null` — the caller renders the plain single-column recap.
 *
 * @param completedSets - set numbers from log-context `completed_sets`.
 * @param serverSets - today's sets from `GET /training/day/{today}`.
 * @param sessionSets - sets saved in THIS session.
 * @param lastSessionSets - `log-context.last_session_sets` (the ghost).
 */
export function buildComparisonRows(
    completedSets: number[],
    serverSets: TrainingSet[],
    sessionSets: SessionSet[],
    lastSessionSets: LogSet[],
): ComparisonRow[] {
    const todayByNum = new Map(
        mergeRecap(completedSets, serverSets, sessionSets).map((r) => [r.set, r]),
    );
    const lastByNum = new Map(lastSessionSets.map((s) => [s.set, s]));
    const nums = new Set<number>([...todayByNum.keys(), ...lastByNum.keys()]);
    return [...nums]
        .sort((a, b) => a - b)
        .map((n) => {
            const today = todayByNum.get(n) ?? null;
            const ghost = lastByNum.get(n);
            const last: FigurePair | null = ghost
                ? { weight: ghost.weight, reps: ghost.reps }
                : null;
            const delta =
                today !== null &&
                today.weight !== null &&
                today.reps !== null &&
                last !== null
                    ? computeDelta(
                          { weight: today.weight, reps: today.reps },
                          last,
                      )
                    : null;
            return { set: n, today, last, delta };
        });
}

/**
 * GYM-130: the NEXT ghost target — the first last-session set with no today
 * entry at all (the standing "beat this" row). Used to auto-scroll the recap
 * to the target on Phase-B entry when the rows overflow. Null when every
 * ghost is already matched (or there is no ghost).
 */
export function findNextGhostSet(rows: ComparisonRow[]): number | null {
    const ghost = rows.find((r) => r.last !== null && r.today === null);
    return ghost ? ghost.set : null;
}

/**
 * GYM-131/132: did a just-saved set beat the matching last-session set?
 * Uses the LOCKED GYM-130 delta rule (weight first, reps tiebreak) against
 * the same-set-number ghost. No ghost for that set number → false (there was
 * nothing to beat — honest, never fabricated).
 */
export function beatsLastSession(
    lastSessionSets: LogSet[],
    saved: SessionSet,
): boolean {
    const last = lastSessionSets.find((s) => s.set === saved.set);
    if (!last) return false;
    const delta = computeDelta(
        { weight: saved.weight, reps: saved.reps },
        { weight: last.weight, reps: last.reps },
    );
    return delta.kind === "up";
}

/**
 * GYM-132: one saved set in the cross-exercise session log. RecordSheet (the
 * session owner) accumulates these via SetLogger's onSetLogged callback;
 * SetLogger computes beatLast/beatPR at save time (it has the comparison
 * context and the effective PR).
 */
export interface SessionLogEntry {
    muscle: string;
    exercise: string;
    set: number;
    weight: number;
    reps: number;
    /** The set beat the matching last-session set (GYM-130 delta = up). */
    beatLast: boolean;
    /** The set strictly beat the effective PR at save time (weight PR). */
    beatPR: boolean;
}

/** GYM-132: the aggregates the session-summary panel renders. */
export interface SessionSummary {
    /** Sets logged this session across ALL exercises. */
    sets: number;
    /** Distinct {muscle, exercise} pairs trained this session. */
    exercises: number;
    /** Σ weight×reps over the session log (kg). */
    volume: number;
    /** How many sets beat their matching last-session set. */
    beatLast: number;
    /** How many weight-PR beats happened this session. */
    prs: number;
}

/**
 * GYM-132: fold the session log into the summary aggregates — pure, all from
 * in-memory data (the zero-network constraint is the spec). An empty log
 * yields all zeros (the caller never shows a summary for it anyway).
 */
export function summarizeSession(log: SessionLogEntry[]): SessionSummary {
    // NUL (escaped below) can't appear in names — an unambiguous pair separator
    // (names may contain spaces, so a visible separator could collide).
    const exercises = new Set(
        log.map((e) => `${e.muscle}\u0000${e.exercise}`),
    );
    return {
        sets: log.length,
        exercises: exercises.size,
        volume: log.reduce((sum, e) => sum + e.weight * e.reps, 0),
        beatLast: log.filter((e) => e.beatLast).length,
        prs: log.filter((e) => e.beatPR).length,
    };
}

/**
 * GYM-104 #3: DERIVED effective PR — no race, no timing dependence.
 *
 * The effective PR is always the greater of:
 *   - the server PR (`ctx.data.pr`) — the real historical record
 *   - the best session set (max weight among sessionSets this session)
 *
 * This replaces the one-shot `prAnchor` useState pattern that caused the race:
 * prAnchor started null; if the user saved a set BEFORE log-context resolved,
 * the PR-beat set prAnchor = <session weight> (e.g. 2.5), and the seed effect
 * `if (pr && prAnchor === null)` then never fired, permanently locking in 2.5
 * instead of the real server PR (80).
 *
 * With the derived approach: once ctx resolves and serverPR.weight = 80, the
 * effective PR is max(80, sessionBest) = 80 — regardless of what session sets
 * were logged before ctx resolved. A 2.5kg session set never hides the real PR.
 *
 * Reps are shown only when the server PR is the effective max (session sets
 * carry no PR-reps source): `PR {w}kg × {r}` vs `PR {w}kg`.
 *
 * @param serverPR - the PR from log-context, or null while unresolved/absent.
 * @param sessionSets - sets saved in THIS session.
 * @returns the chip model, or null when nothing is known yet.
 */
export function computeEffectivePR(
    serverPR: PersonalRecord | null,
    sessionSets: SessionSet[],
): EffectivePR | null {
    const serverWeight = serverPR?.weight ?? -Infinity;
    const sessionBestWeight = sessionSets.reduce<number>(
        (best, s) => Math.max(best, s.weight),
        -Infinity,
    );
    if (serverWeight === -Infinity && sessionBestWeight === -Infinity) {
        return null;
    }
    const effectiveWeight = Math.max(serverWeight, sessionBestWeight);
    // Show reps only when the server PR is the source (session sets have no reps).
    const effectiveReps =
        serverPR && serverPR.weight >= sessionBestWeight ? serverPR.reps : null;
    return { weight: effectiveWeight, reps: effectiveReps };
}

/**
 * GYM-133: the kind of PR a just-saved set beat — exactly one (or none) per
 * save, resolved by {@link resolvePrBeat} with the hierarchy
 * weight > reps-at-weight > e1rm. Calibration (doc 03 §4.1): "weight" keeps
 * the full GYM-131 celebration (banner + pulse + flare); the other two are
 * QUIET — pulse + flare only, no banner.
 */
export type PrBeatKind = "weight" | "reps-at-weight" | "e1rm";

/**
 * GYM-133: resolve which PR type (if any) a just-saved set beat.
 *
 * Hierarchy (one celebration per save, highest wins):
 *  1. **weight** — strictly beats the effective PR weight (or the first set
 *     ever, when no PR source exists at all) — the pre-existing GYM-104/131
 *     `beat` semantics, unchanged.
 *  2. **reps-at-weight** — the weight EQUALS a previously-lifted weight and
 *     the reps strictly exceed the best-known reps at that weight.
 *  3. **e1rm** — the set's Epley e1RM strictly exceeds the best-known e1RM.
 *
 * HONESTY / DATA LIMITATION (accepted GYM-133 scope): the client only holds
 * log-context (`last_session_sets` + `pr`) plus this session's saved sets —
 * NOT the full training history. "Best known reps at this weight" and "best
 * known e1RM" are therefore LOWER BOUNDS over that pool: a quiet celebration
 * may occasionally fire for a set that an older, unseen session already beat.
 * It can never miss a real weight PR (the pr field IS the full history's
 * max). GYM-134's server-computed trend endpoint replaces the heuristic.
 *
 * @param serverPR - the PR from log-context, or null while unresolved/absent.
 * @param lastSessionSets - `log-context.last_session_sets` (the ghost).
 * @param sessionSets - sets saved earlier THIS session (PRE-save list).
 * @param saved - the just-saved set.
 * @returns the beaten PR kind, or null when nothing known was beaten.
 */
export function resolvePrBeat(
    serverPR: PersonalRecord | null,
    lastSessionSets: LogSet[],
    sessionSets: SessionSet[],
    saved: SessionSet,
): PrBeatKind | null {
    // 1. Weight PR — identical to the pre-GYM-133 `beat` check: strictly
    //    above the derived effective PR, or the first set with no PR source.
    const effective = computeEffectivePR(serverPR, sessionSets);
    if (effective === null || saved.weight > effective.weight) return "weight";

    // The known-history pool for the quiet types (lower-bound heuristic —
    // see the docblock): server PR + last session + this session's sets.
    const known: FigurePair[] = [
        ...(serverPR ? [{ weight: serverPR.weight, reps: serverPR.reps }] : []),
        ...lastSessionSets.map((s) => ({ weight: s.weight, reps: s.reps })),
        ...sessionSets.map((s) => ({ weight: s.weight, reps: s.reps })),
    ];

    // 2. Reps-at-weight PR — the weight was lifted before (in the pool) and
    //    the reps strictly beat the best reps known at exactly that weight.
    const repsAtWeight = known
        .filter((k) => k.weight === saved.weight)
        .map((k) => k.reps);
    if (repsAtWeight.length > 0 && saved.reps > Math.max(...repsAtWeight)) {
        return "reps-at-weight";
    }

    // 3. e1RM PR — strictly beats the best Epley e1RM over the same pool.
    //    (Empty pool can't happen here: effective !== null implies a source.)
    if (known.length > 0) {
        const bestKnown = Math.max(...known.map((k) => epley(k.weight, k.reps)));
        if (epley(saved.weight, saved.reps) > bestKnown) return "e1rm";
    }
    return null;
}

/**
 * GYM-152: pure prefill selection — the approved priority order for §12.3.
 *
 * Priority:
 *  1. `lastSessionSets` matched by `nextSet` (last training's same set N).
 *  2. Fallback: repeat `sessionSets[last]` (more sets than last time, or new
 *     exercise with prior sets in THIS session).
 *  3. Null pair (both null) — Save stays disabled until the user types.
 *
 * This is a pure helper so the selection logic is unit-testable without React.
 * SetLogger calls it inside the prefill `useEffect`.
 *
 * @param nextSet - the upcoming set number (1-based).
 * @param sessionSets - sets already logged in THIS session for this exercise.
 * @param lastSessionSets - `log-context.last_session_sets` (may be empty).
 * @returns `{weight, reps}` to prefill, or `{weight: null, reps: null}`.
 */
export function derivePrefill(
    nextSet: number,
    sessionSets: SessionSet[],
    lastSessionSets: LogSet[],
): { weight: number | null; reps: number | null } {
    // Priority 1: last training's same set number.
    const fromLast = lastSessionSets.find((s) => s.set === nextSet);
    if (fromLast) {
        return { weight: fromLast.weight, reps: fromLast.reps };
    }
    // Priority 2: repeat this session's last set (exercise is new or has more
    // sets than last training — gives a sensible starting point).
    const lastInSession = sessionSets[sessionSets.length - 1];
    if (lastInSession) {
        return { weight: lastInSession.weight, reps: lastInSession.reps };
    }
    // Priority 3: nothing known — leave empty.
    return { weight: null, reps: null };
}

/**
 * GYM-125 #2: inline save-error message for the SetLogger write path
 * (spec §12.5 / §12.8). A 409 from `POST /training` means the attempted set
 * NUMBER already exists for this exercise today (set-number collision — e.g.
 * the set was logged from another device or via the bot). That case gets a
 * specific message; the log-context invalidation that `useCreateTraining`
 * fans out on settle then refetches `completed_sets`, so `computeNextSet`
 * auto-corrects ("refreshed your numbers"). Every other failure keeps the
 * generic retry message.
 *
 * @param error - the mutation error (`create.error`); any unknown shape.
 * @param attemptedSet - the set number the failed save tried to write.
 * @param locale - explicit locale for deterministic tests; defaults active.
 */
export function saveErrorMessage(
    error: unknown,
    attemptedSet: number,
    locale: Locale = getLocale(),
): string {
    if (error instanceof ApiError && error.status === 409) {
        return translate(locale, "save.error409", { n: attemptedSet });
    }
    return translate(locale, "save.errorGeneric");
}
