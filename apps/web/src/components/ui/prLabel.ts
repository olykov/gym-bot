/**
 * Pure utility for GYM-153: PR label key derivation.
 *
 * Separated from SetRow.tsx so react-refresh does not complain about
 * exporting non-component values from a component module.
 */
import type { MessageKey } from "@/i18n/messages";

/**
 * Map `pr_kind` to the pair of i18n message keys used by the SetRow
 * middle PR marker: `[fullKey, shortKey]`.
 *
 * - `fullKey`:  the kind-specific label — "pr.weight" | "pr.reps" — shown
 *   on wider rows. Falls back to "pr" when `pr_kind` is null (defensive).
 * - `shortKey`: always "pr" — the collapsed label shown on very narrow rows
 *   (≤ 260px container) via CSS container-query.
 */
export function prLabelKeys(
    pr_kind: "weight" | "reps" | null,
): [MessageKey, MessageKey] {
    if (pr_kind === "weight") return ["pr.weight", "pr"];
    if (pr_kind === "reps") return ["pr.reps", "pr"];
    return ["pr", "pr"];
}
