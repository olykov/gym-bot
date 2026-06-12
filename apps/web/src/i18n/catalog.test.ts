/**
 * Unit tests for the GYM-109 string catalog: interpolation, Intl plural rules
 * (ru one/few/many, en one/other), muscle-label localization (pass-through
 * for unknown names) and the t()/translate() locale defaulting. The en/ru
 * exhaustiveness itself is enforced at compile time by the catalog types.
 */
import { describe, expect, it } from "vitest";
import {
    localizeMuscleName,
    plural,
    t,
    tPlural,
    translate,
    translatePlural,
} from "./catalog";
import type { PluralForms } from "./messages";

describe("translate / t (interpolation)", () => {
    it("resolves a plain key per locale", () => {
        expect(translate("en", "common.cancel")).toBe("Cancel");
        expect(translate("ru", "common.cancel")).toBe("Отмена");
    });

    it("interpolates {name}-style params (string and number)", () => {
        expect(translate("en", "logger.saveSet", { n: 4 })).toBe("Save set 4");
        expect(translate("ru", "logger.saveSet", { n: 4 })).toBe(
            "Записать сет 4",
        );
        expect(
            translate("en", "picker.alreadyHave", { name: "Bench Press" }),
        ).toBe('You already have "Bench Press".');
    });

    it("leaves unknown placeholders verbatim (visible typo, fail-soft)", () => {
        expect(translate("en", "logger.saveSet", { wrong: 1 })).toBe(
            "Save set {n}",
        );
    });

    it("t() defaults to the resolved locale (en outside Telegram)", () => {
        expect(t("common.done")).toBe("Done");
        expect(tPlural("count.sets", 2)).toBe("2 sets");
    });
});

describe("plural (Intl.PluralRules)", () => {
    const ruForms: PluralForms = {
        one: "сет",
        few: "сета",
        many: "сетов",
        other: "сета",
    };

    it("picks ru one/few/many correctly", () => {
        expect(plural(1, ruForms, "ru")).toBe("сет");
        expect(plural(21, ruForms, "ru")).toBe("сет");
        expect(plural(2, ruForms, "ru")).toBe("сета");
        expect(plural(34, ruForms, "ru")).toBe("сета");
        expect(plural(5, ruForms, "ru")).toBe("сетов");
        expect(plural(11, ruForms, "ru")).toBe("сетов");
        expect(plural(100, ruForms, "ru")).toBe("сетов");
    });

    it("falls back to `other` for ru fractions", () => {
        expect(plural(1.5, ruForms, "ru")).toBe("сета");
    });

    it("picks en one/other correctly", () => {
        const enForms: PluralForms = { one: "set", other: "sets" };
        expect(plural(1, enForms, "en")).toBe("set");
        expect(plural(0, enForms, "en")).toBe("sets");
        expect(plural(21, enForms, "en")).toBe("sets");
    });

    it("falls back to `other` when a category form is missing", () => {
        const sparse: PluralForms = { other: "штук" };
        expect(plural(1, sparse, "ru")).toBe("штук");
    });
});

describe("translatePlural (countable catalog entries)", () => {
    it("renders en counts", () => {
        expect(translatePlural("en", "count.exercises", 1)).toBe("1 exercise");
        expect(translatePlural("en", "count.exercises", 3)).toBe("3 exercises");
        expect(translatePlural("en", "count.sets", 1)).toBe("1 set");
        expect(translatePlural("en", "count.sets", 0)).toBe("0 sets");
    });

    it("renders ru counts across all three forms", () => {
        expect(translatePlural("ru", "count.sets", 1)).toBe("1 сет");
        expect(translatePlural("ru", "count.sets", 3)).toBe("3 сета");
        expect(translatePlural("ru", "count.sets", 7)).toBe("7 сетов");
        expect(translatePlural("ru", "count.exercises", 1)).toBe(
            "1 упражнение",
        );
        expect(translatePlural("ru", "count.exercises", 2)).toBe(
            "2 упражнения",
        );
        expect(translatePlural("ru", "count.exercises", 12)).toBe(
            "12 упражнений",
        );
        expect(translatePlural("ru", "count.exercises", 21)).toBe(
            "21 упражнение",
        );
    });
});

describe("localizeMuscleName (ADR 0003 Channel A)", () => {
    it("maps the 8 canonical names to ru labels", () => {
        expect(localizeMuscleName("Chest", "ru")).toBe("Грудь");
        expect(localizeMuscleName("Back", "ru")).toBe("Спина");
        expect(localizeMuscleName("ABS", "ru")).toBe("Пресс");
        expect(localizeMuscleName("Legs", "ru")).toBe("Ноги");
        expect(localizeMuscleName("Shoulders", "ru")).toBe("Плечи");
        expect(localizeMuscleName("Biceps", "ru")).toBe("Бицепс");
        expect(localizeMuscleName("Triceps", "ru")).toBe("Трицепс");
        expect(localizeMuscleName("Forearms", "ru")).toBe("Предплечья");
    });

    it("keeps en labels canonical", () => {
        expect(localizeMuscleName("Chest", "en")).toBe("Chest");
        expect(localizeMuscleName("ABS", "en")).toBe("ABS");
    });

    it("matches case-insensitively (API casing is authoritative anyway)", () => {
        expect(localizeMuscleName("chest", "ru")).toBe("Грудь");
        expect(localizeMuscleName("  Legs  ", "ru")).toBe("Ноги");
    });

    it("passes unknown / user-created names through unchanged", () => {
        expect(localizeMuscleName("Neck", "ru")).toBe("Neck");
        expect(localizeMuscleName("Моя мышца", "ru")).toBe("Моя мышца");
        expect(localizeMuscleName("", "ru")).toBe("");
    });
});
