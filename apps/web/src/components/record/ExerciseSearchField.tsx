/**
 * Search-and-pick control for the add-exercise flow (GYM-94, ADR 0003 Channel B).
 *
 * Replaces the bare free-text `+ Exercise` add-inline field on the exercise step
 * of RecordPicker. Behavior:
 *
 *  1. A search input (≥44px, Chalk & Iron tokens) — debounced ~250ms.
 *  2. As the user types, ranked candidates from `GET /exercises/search?muscle_id=&lang=`
 *     appear below the input as a list of tappable rows.
 *  3. Tapping a candidate calls `onPick` with that exercise's name — the same
 *     downstream path as tapping an existing tile.
 *  4. A "Create «typed text»" row is always available as the last item in the list
 *     (or as the only option when no candidates match), so free-text creation
 *     remains accessible but is visually de-prioritised.
 *  5. When the query is empty the list collapses entirely (no phantom empty state).
 *
 * States:
 *  - Loading (fresh query in-flight): a single skeleton row below the input.
 *  - Error: a quiet inline message with a retry link.
 *  - No candidates: only the "Create" row appears (plus the "Nothing found" hint).
 *
 * Design (Chalk & Iron, tokens only):
 *  - Input: `--secondary-bg` fill, `--hairline` border, `--text` / `--hint`
 *    placeholder, 12px radius token, 44px min-height.
 *  - Candidate rows: `--bg` surface, hairline border, `--secondary-bg` hover/press
 *    state (press-95). Name in Sora 400 `--text`; muscle label in Sora `--hint`
 *    when cross-muscle (muscle_id omitted). A subtle `--hint` match-reason badge
 *    (exact / alias / fuzzy) for the first ~3 results to give the user confidence.
 *    Match-reason badge: 'exact' and 'prefix' are NEVER shown (they look like any
 *    normal name match and adding a badge would be noise); 'alias' → "also known as";
 *    'fuzzy' → small `--hint` italic "(typo match)" to reassure the user they didn't
 *    mistype. Shown only when `q.trim().length >= 2` (single-char matches are not
 *    informative enough to badge).
 *  - Create row: dashed hairline, `--hint` text with `--accent` emphasis on the
 *    typed name; sits AFTER candidates as a clear last-resort affordance.
 *  - The list is `max-h-[256px] overflow-y-auto` so it never pushes the sheet out
 *    of bounds on a long catalog hit; the BottomSheet's own `--keyboard-pad` var
 *    keeps the input above the keyboard.
 */
import { useEffect, useRef, useState } from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { EXERCISE_NAME_MAX } from "@/validation";
import { useExerciseSearch, type ExerciseCandidate } from "@/hooks/useRecord";
import { useLocale } from "@/i18n/locale";

/** Debounce interval in ms (per GYM-94 spec: ~250ms). */
const DEBOUNCE_MS = 250;

/** Maximum candidates shown before the Create row. */
const MAX_CANDIDATES = 8;

interface ExerciseSearchFieldProps {
    /** Muscle name (display) — for placeholder text and the Create mutation. */
    muscleName: string;
    /** Numeric id of the selected muscle — passed as muscle_id scope to the search API. */
    muscleId: number;
    /** Propagated to the parent's create-exercise mutation (same path as the old add-inline). */
    pending?: boolean;
    /** Error string from the create mutation — shown below the field. */
    error?: string | null;
    /**
     * Called when the user PICKS an existing candidate (taps a search result).
     * The name passed is the canonical exercise name from the API.
     */
    onPick: (exerciseName: string) => void;
    /**
     * Called when the user submits a FREE-TEXT create (taps the "Create «…»" row
     * or presses Enter when no candidate is focused). Passes the trimmed name.
     */
    onCreate: (name: string) => void;
    /** Called when the user presses the × cancel button. */
    onCancel: () => void;
    /** tabIndex forwarded to the input (mirrors RecordPicker's step-based tabIndex). */
    tabIndex?: number;
}

/**
 * Small badge rendered beside a candidate to explain *why* it matched.
 * Only shown for 'alias' and 'fuzzy' (not 'exact'/'prefix' — those are obvious).
 */
function MatchBadge({ reason }: { reason: ExerciseCandidate["match_reason"] }) {
    if (reason === "exact" || reason === "prefix") return null;
    return (
        <span className="ml-2 shrink-0 text-[11px] italic text-hint">
            {reason === "alias" ? "aka" : "~"}
        </span>
    );
}

export function ExerciseSearchField({
    muscleName,
    muscleId,
    pending = false,
    error = null,
    onPick,
    onCreate,
    onCancel,
    tabIndex = 0,
}: ExerciseSearchFieldProps) {
    const locale = useLocale();

    // Raw input value (unDebounced — drives the visible input).
    const [inputValue, setInputValue] = useState("");
    // Debounced query — drives the search API call.
    const [debouncedQ, setDebouncedQ] = useState("");

    const inputRef = useRef<HTMLInputElement>(null);

    // Focus the input on mount (mirrors AddInlineField autoFocus).
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    // Debounce the input value → debouncedQ.
    useEffect(() => {
        const id = setTimeout(() => {
            setDebouncedQ(inputValue);
        }, DEBOUNCE_MS);
        return () => clearTimeout(id);
    }, [inputValue]);

    const trimmedQ = inputValue.trim();
    const search = useExerciseSearch(debouncedQ, muscleId, locale, MAX_CANDIDATES);

    const candidates = search.data ?? [];
    const showList = trimmedQ.length > 0;
    // Only show badge hints when query is long enough to be meaningful.
    const showBadges = trimmedQ.length >= 2;

    function handlePick(name: string): void {
        onPick(name);
    }

    function handleCreate(): void {
        if (!trimmedQ || pending) return;
        onCreate(trimmedQ);
    }

    function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>): void {
        if (e.key === "Enter") {
            e.preventDefault();
            // If there are candidates, pick the top one on Enter.
            if (candidates.length > 0) {
                handlePick(candidates[0].name);
            } else if (trimmedQ) {
                handleCreate();
            }
        }
        if (e.key === "Escape") {
            onCancel();
        }
    }

    return (
        <div>
            {/* ── Input row ─────────────────────────────────────────────── */}
            <div className="flex items-stretch gap-2">
                <div className="relative flex-1">
                    {/* Search icon — a subtle affordance inside the input */}
                    <span
                        aria-hidden
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-hint"
                        style={{ fontSize: "15px", lineHeight: 1 }}
                    >
                        ⌕
                    </span>
                    <input
                        ref={inputRef}
                        type="text"
                        inputMode="text"
                        autoCapitalize="words"
                        autoComplete="off"
                        autoCorrect="off"
                        spellCheck={false}
                        tabIndex={tabIndex}
                        value={inputValue}
                        maxLength={EXERCISE_NAME_MAX}
                        placeholder={`Search in ${muscleName}…`}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className="min-h-[44px] w-full rounded-md border border-hairline bg-secondary-bg py-2 pl-8 pr-3 text-base text-text outline-none placeholder:text-hint focus:border-accent"
                    />
                </div>
                <button
                    type="button"
                    onClick={onCancel}
                    aria-label="Cancel search"
                    tabIndex={tabIndex}
                    className="press-95 min-h-[44px] shrink-0 rounded-md border border-hairline bg-bg px-3 text-base text-hint"
                >
                    ×
                </button>
            </div>

            {/* ── Error from create mutation ─────────────────────────── */}
            {error ? (
                <p className="mt-2 text-label text-accent">{error}</p>
            ) : null}

            {/* ── Candidate list (only when there is input) ─────────── */}
            {showList ? (
                <div
                    className="mt-2 overflow-y-auto rounded-md border border-hairline bg-bg"
                    style={{ maxHeight: "256px" }}
                    role="listbox"
                    aria-label={`Exercise suggestions for ${muscleName}`}
                >
                    {/* Loading skeleton — one row while the search is in-flight. */}
                    {search.isFetching && candidates.length === 0 ? (
                        <div className="px-3 py-2">
                            <Skeleton className="h-[40px] w-full rounded" />
                        </div>
                    ) : null}

                    {/* Error from the search query itself. */}
                    {search.isError && !search.isFetching ? (
                        <div className="px-3 py-2">
                            <p className="text-label text-hint">
                                Search unavailable.{" "}
                                <button
                                    type="button"
                                    tabIndex={tabIndex}
                                    onClick={() => void search.refetch()}
                                    className="text-accent underline"
                                >
                                    Retry
                                </button>
                            </p>
                        </div>
                    ) : null}

                    {/* Candidates — ranked best-first. */}
                    {candidates.map((c) => (
                        <button
                            key={c.id}
                            type="button"
                            role="option"
                            aria-selected={false}
                            tabIndex={tabIndex}
                            onClick={() => handlePick(c.name)}
                            className="press-95 flex min-h-[44px] w-full items-center gap-2 border-b border-hairline px-3 py-2 text-left last:border-b-0 active:bg-secondary-bg"
                        >
                            <span className="min-w-0 flex-1 truncate text-base text-text" title={c.name}>
                                {c.name}
                            </span>
                            {showBadges ? (
                                <MatchBadge reason={c.match_reason} />
                            ) : null}
                        </button>
                    ))}

                    {/* "No suggestions" hint — only shown when search finished with no results. */}
                    {!search.isFetching && !search.isError && candidates.length === 0 && debouncedQ.trim() ? (
                        <div className="px-3 py-2">
                            <p className="text-label text-hint">No matches — create it below.</p>
                        </div>
                    ) : null}

                    {/* "Create «typed text»" — always last, clearly a last resort.
                        Shown as long as there is typed text (even if suggestions exist). */}
                    {trimmedQ ? (
                        <button
                            type="button"
                            tabIndex={tabIndex}
                            disabled={pending}
                            onClick={handleCreate}
                            className="press-95 flex min-h-[44px] w-full items-center gap-2 border-t border-dashed border-hairline px-3 py-2 text-left disabled:opacity-40"
                        >
                            <span className="text-label text-hint">Create</span>
                            <span
                                className="min-w-0 flex-1 truncate text-base font-semibold text-accent"
                                title={trimmedQ}
                            >
                                «{trimmedQ}»
                            </span>
                            {pending ? (
                                <span className="shrink-0 text-label text-hint">…</span>
                            ) : null}
                        </button>
                    ) : null}
                </div>
            ) : null}
        </div>
    );
}
