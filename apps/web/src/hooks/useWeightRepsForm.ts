/**
 * The one weight/reps form state (GYM-126) — consolidates the triplicated
 * `weightText/repsText + parseNumeric + valid` logic from SetLogger, SetEditor
 * and AddSetInline.
 *
 * The hook owns ONLY the shared mechanics:
 *  - raw text state for both fields (a partial entry like "10." never fights
 *    the user — the parse runs beside the text, spec §11.7);
 *  - parsing via the Stepper's own `parseNumeric` contract (comma→dot,
 *    weight decimal / reps integer);
 *  - the shared validity rule: both parse non-null and are >= 0;
 *  - spread-ready `weightProps` / `repsProps` for the two <Stepper>s
 *    (min/step/inputMode/integer baked in — WEIGHT_STEP lives here once).
 *
 * Call-site semantics deliberately stay at the call sites and compose on top:
 *  - SetEditor adds its changed-from-original check (`weight !== set.weight`);
 *  - AddSetInline adds `!isPending` to its submit-enable and re-prefills via
 *    `reset(...)` each time the inline form opens;
 *  - SetLogger drives its §12.3 pre-fill effect through `weightText/repsText`
 *    + `setWeightText/setRepsText` (only filling EMPTY fields — exact
 *    behavior preserved).
 *
 * `reset` is identity-stable (useCallback, setter-only) so effects may list it
 * in their dependency arrays without re-running.
 */
import { useCallback, useState } from "react";
import { parseNumeric } from "@/components/ui/Stepper";
import { WEIGHT_STEP } from "@/validation";

/** Initial / reset payload — raw text, matching what the fields hold. */
export interface WeightRepsTexts {
    weightText?: string;
    repsText?: string;
}

interface StepperFieldProps {
    value: number | null;
    text: string;
    onChange: (next: { text: string; value: number | null }) => void;
    min: number;
    step: number;
    integer?: boolean;
    inputMode: "decimal" | "numeric";
}

export interface WeightRepsForm {
    /** Raw text the weight field holds (e.g. "10." mid-entry). */
    weightText: string;
    /** Raw text the reps field holds. */
    repsText: string;
    /** Parsed weight (comma-normalized), or null when empty/invalid. */
    weight: number | null;
    /** Parsed integer reps, or null when empty/invalid. */
    reps: number | null;
    /** Both fields parse and are non-negative — the shared Save gate. */
    valid: boolean;
    /** Spread onto the Weight <Stepper> (label/unit stay at the call site). */
    weightProps: StepperFieldProps;
    /** Spread onto the Reps <Stepper>. */
    repsProps: StepperFieldProps;
    setWeightText: (text: string) => void;
    setRepsText: (text: string) => void;
    /** Reset both fields (empty by default, or to the given texts). Stable. */
    reset: (next?: WeightRepsTexts) => void;
}

/**
 * Shared weight/reps form state for the three set forms.
 *
 * @param initial - optional initial raw texts (SetEditor: the original set;
 *   AddSetInline: the last set's values). Omitted → both fields start empty.
 */
export function useWeightRepsForm(initial?: WeightRepsTexts): WeightRepsForm {
    const [weightText, setWeightText] = useState(initial?.weightText ?? "");
    const [repsText, setRepsText] = useState(initial?.repsText ?? "");

    const weight = parseNumeric(weightText, false);
    const reps = parseNumeric(repsText, true);

    const valid =
        weight !== null && weight >= 0 && reps !== null && reps >= 0;

    const reset = useCallback((next?: WeightRepsTexts): void => {
        setWeightText(next?.weightText ?? "");
        setRepsText(next?.repsText ?? "");
    }, []);

    return {
        weightText,
        repsText,
        weight,
        reps,
        valid,
        weightProps: {
            value: weight,
            text: weightText,
            onChange: ({ text }) => setWeightText(text),
            min: 0,
            step: WEIGHT_STEP,
            inputMode: "decimal",
        },
        repsProps: {
            value: reps,
            text: repsText,
            onChange: ({ text }) => setRepsText(text),
            min: 0,
            step: 1,
            integer: true,
            inputMode: "numeric",
        },
        setWeightText,
        setRepsText,
        reset,
    };
}
