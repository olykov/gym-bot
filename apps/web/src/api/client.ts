/**
 * Typed fetch wrapper over the Core API (spec §1, §4).
 *
 * Request/response shapes come from the generated TypeScript client in
 * packages/api-contract/clients/typescript/schema.ts — the single source of
 * truth for the contract. This wrapper attaches the session JWT, prefixes the
 * API base, and surfaces a typed ApiError; it is the ONLY place the app talks
 * HTTP (no fetch sprawl, no axios — per the spec).
 */
import type { components, paths } from "@api-contract/schema";
import { getSessionToken } from "./session";

/** API base — mirrors apps/admin (`/api/v1`), proxied by nginx/Vite. */
export const API_BASE = "/api/v1";

export type Schemas = components["schemas"];
export type ApiPaths = paths;

export class ApiError extends Error {
    constructor(
        public readonly status: number,
        message: string,
        public readonly detail?: unknown,
    ) {
        super(message);
        this.name = "ApiError";
    }
}

interface RequestOptions {
    method?: "GET" | "POST" | "PUT" | "DELETE";
    body?: unknown;
    /** Skip the Authorization header (used by the auth endpoints). */
    anonymous?: boolean;
    signal?: AbortSignal;
}

/**
 * Perform a typed JSON request against the Core API.
 *
 * @param path - API path relative to {@link API_BASE} (e.g. "/analytics/summary").
 * @param options - method/body/auth options.
 * @returns the parsed JSON response, typed by the caller's generic.
 * @throws {ApiError} on a non-2xx response or a network failure.
 */
export async function apiRequest<TResponse>(
    path: string,
    options: RequestOptions = {},
): Promise<TResponse> {
    const { method = "GET", body, anonymous = false, signal } = options;

    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";

    if (!anonymous) {
        const token = getSessionToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;
    }

    let res: Response;
    try {
        res = await fetch(`${API_BASE}${path}`, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
            signal,
        });
    } catch (err) {
        throw new ApiError(0, "Network request failed", err);
    }

    const text = await res.text();
    const data = text ? safeJson(text) : undefined;

    if (!res.ok) {
        const detail =
            (data as { detail?: string } | undefined)?.detail ??
            res.statusText;
        throw new ApiError(res.status, String(detail), data);
    }

    return data as TResponse;
}

function safeJson(text: string): unknown {
    try {
        return JSON.parse(text);
    } catch {
        return text;
    }
}
