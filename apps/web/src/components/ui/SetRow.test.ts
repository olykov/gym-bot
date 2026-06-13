/**
 * Unit tests for the SetRow PR label pure logic (GYM-153).
 *
 * `prLabelKeys` lives in its own module (prLabel.ts) so react-refresh does
 * not flag the component file. This suite tests the pure mapping function
 * only — no DOM, no React.
 */
import { describe, expect, it } from "vitest";
import { prLabelKeys } from "./prLabel";

describe("prLabelKeys", () => {
    it('maps "weight" pr_kind to pr.weight full key', () => {
        const [full, short] = prLabelKeys("weight");
        expect(full).toBe("pr.weight");
        expect(short).toBe("pr");
    });

    it('maps "reps" pr_kind to pr.reps full key', () => {
        const [full, short] = prLabelKeys("reps");
        expect(full).toBe("pr.reps");
        expect(short).toBe("pr");
    });

    it("maps null pr_kind (defensive fallback) to short pr key for both slots", () => {
        const [full, short] = prLabelKeys(null);
        expect(full).toBe("pr");
        expect(short).toBe("pr");
    });

    it("always returns pr as the short fallback regardless of kind", () => {
        for (const kind of ["weight", "reps", null] as const) {
            const [, short] = prLabelKeys(kind);
            expect(short).toBe("pr");
        }
    });
});
