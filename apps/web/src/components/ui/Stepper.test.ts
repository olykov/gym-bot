/**
 * Unit tests for the Stepper's pure input parser (GYM-124).
 * DOM behavior (bump/clamp via buttons) is out of scope this wave — pure
 * logic only, no jsdom/RTL yet.
 */
import { describe, expect, it, vi } from "vitest";

// GYM-122: Stepper now imports the haptic helper, whose @twa-dev/sdk touches
// `window` at import time — mock the wrapper so this pure-parser suite keeps
// running in the node environment (no jsdom).
vi.mock("@/telegram/webapp", () => ({ hapticImpact: vi.fn() }));

import { parseNumeric } from "./Stepper";

describe("parseNumeric (decimal mode)", () => {
    it("parses a plain number", () => {
        expect(parseNumeric("12.5", false)).toBe(12.5);
        expect(parseNumeric("80", false)).toBe(80);
    });

    it("normalizes a decimal comma to a dot (locale keyboards)", () => {
        expect(parseNumeric("12,5", false)).toBe(12.5);
        expect(parseNumeric("0,25", false)).toBe(0.25);
    });

    it("returns null for empty or whitespace-only input", () => {
        expect(parseNumeric("", false)).toBeNull();
        expect(parseNumeric("   ", false)).toBeNull();
    });

    it("returns null for non-numeric input", () => {
        expect(parseNumeric("abc", false)).toBeNull();
        expect(parseNumeric("-", false)).toBeNull();
        expect(parseNumeric(".", false)).toBeNull();
    });

    it("accepts a trailing dot mid-entry as the integer part", () => {
        expect(parseNumeric("10.", false)).toBe(10);
        expect(parseNumeric("10,", false)).toBe(10);
    });

    it("trims surrounding whitespace", () => {
        expect(parseNumeric(" 8 ", false)).toBe(8);
    });
});

describe("parseNumeric (integer mode)", () => {
    it("parses whole numbers", () => {
        expect(parseNumeric("12", true)).toBe(12);
    });

    it("truncates a decimal entry to its integer part", () => {
        expect(parseNumeric("10.9", true)).toBe(10);
        expect(parseNumeric("10,9", true)).toBe(10);
    });

    it("returns null for empty and non-numeric input", () => {
        expect(parseNumeric("", true)).toBeNull();
        expect(parseNumeric("reps", true)).toBeNull();
    });
});
