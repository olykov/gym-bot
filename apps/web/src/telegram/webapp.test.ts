/**
 * Unit tests for the BackButton handler stack (GYM-119).
 *
 * The invariants under test: exactly ONE underlying SDK onClick subscription
 * (created lazily), dispatch to the TOP of the stack only, single-owner
 * visibility (show while non-empty, hide when it empties), out-of-order pop,
 * and double-pop safety. The SDK is mocked; vi.resetModules() gives every
 * test a fresh module-level stack.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

interface BackButtonMock {
    onClick: ReturnType<typeof vi.fn>;
    offClick: ReturnType<typeof vi.fn>;
    show: ReturnType<typeof vi.fn>;
    hide: ReturnType<typeof vi.fn>;
}

interface SdkMock {
    initData: string;
    BackButton: BackButtonMock;
}

vi.mock("@twa-dev/sdk", () => ({
    default: {
        initData: "",
        BackButton: {
            onClick: vi.fn(),
            offClick: vi.fn(),
            show: vi.fn(),
            hide: vi.fn(),
        },
    },
}));

/** Fresh webapp module + fresh SDK mock per test (module-level stack resets). */
async function load() {
    vi.resetModules();
    const webapp = await import("./webapp");
    const sdk = (await import("@twa-dev/sdk")).default as unknown as SdkMock;
    return { webapp, sdk };
}

/** The dispatcher the stack registered with the SDK (the ONE subscription). */
function dispatcher(sdk: SdkMock): () => void {
    const call = sdk.BackButton.onClick.mock.calls[0] as Array<() => void>;
    return call[0];
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("pushBackHandler — SDK subscription", () => {
    it("subscribes lazily and exactly once across many pushes", async () => {
        const { webapp, sdk } = await load();
        expect(sdk.BackButton.onClick).not.toHaveBeenCalled();

        const popA = webapp.pushBackHandler(() => undefined);
        expect(sdk.BackButton.onClick).toHaveBeenCalledTimes(1);

        const popB = webapp.pushBackHandler(() => undefined);
        expect(sdk.BackButton.onClick).toHaveBeenCalledTimes(1);

        popB();
        popA();
        webapp.pushBackHandler(() => undefined);
        expect(sdk.BackButton.onClick).toHaveBeenCalledTimes(1);
    });
});

describe("pushBackHandler — dispatch order", () => {
    it("dispatches to the TOP handler only", async () => {
        const { webapp, sdk } = await load();
        const a = vi.fn();
        const b = vi.fn();
        webapp.pushBackHandler(a);
        webapp.pushBackHandler(b);

        dispatcher(sdk)();
        expect(b).toHaveBeenCalledTimes(1);
        expect(a).not.toHaveBeenCalled();
    });

    it("the layer below regains Back when the top pops", async () => {
        const { webapp, sdk } = await load();
        const a = vi.fn();
        const b = vi.fn();
        webapp.pushBackHandler(a);
        const popB = webapp.pushBackHandler(b);

        popB();
        dispatcher(sdk)();
        expect(a).toHaveBeenCalledTimes(1);
        expect(b).not.toHaveBeenCalled();
    });

    it("popping a MIDDLE entry leaves the top in charge", async () => {
        const { webapp, sdk } = await load();
        const a = vi.fn();
        const b = vi.fn();
        const popA = webapp.pushBackHandler(a);
        webapp.pushBackHandler(b);

        popA(); // out-of-order pop (a sits below b)
        dispatcher(sdk)();
        expect(b).toHaveBeenCalledTimes(1);
        expect(a).not.toHaveBeenCalled();
    });

    it("does nothing on an empty stack", async () => {
        const { webapp, sdk } = await load();
        const a = vi.fn();
        const popA = webapp.pushBackHandler(a);
        popA();
        expect(() => dispatcher(sdk)()).not.toThrow();
        expect(a).not.toHaveBeenCalled();
    });
});

describe("pushBackHandler — visibility (single owner)", () => {
    it("shows on first push and hides only when the stack empties", async () => {
        const { webapp, sdk } = await load();
        const popA = webapp.pushBackHandler(() => undefined);
        expect(sdk.BackButton.show).toHaveBeenCalledTimes(1);
        expect(sdk.BackButton.hide).not.toHaveBeenCalled();

        const popB = webapp.pushBackHandler(() => undefined);
        popB(); // one entry left — still visible
        expect(sdk.BackButton.hide).not.toHaveBeenCalled();
        expect(sdk.BackButton.show).toHaveBeenCalledTimes(3);

        popA(); // stack empty — hide
        expect(sdk.BackButton.hide).toHaveBeenCalledTimes(1);
    });
});

describe("pushBackHandler — double-pop safety", () => {
    it("a second pop is a no-op and never removes someone else's entry", async () => {
        const { webapp, sdk } = await load();
        const a = vi.fn();
        const b = vi.fn();
        const popA = webapp.pushBackHandler(a);
        popA();
        const popB = webapp.pushBackHandler(b);
        popA(); // double pop — must NOT remove b

        dispatcher(sdk)();
        expect(b).toHaveBeenCalledTimes(1);
        expect(sdk.BackButton.hide).toHaveBeenCalledTimes(1); // only the real empty
        popB();
        expect(sdk.BackButton.hide).toHaveBeenCalledTimes(2);
    });
});
