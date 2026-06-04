/**
 * Mini App auth round-trip (spec §4).
 *
 * Mirrors apps/admin/src/pages/Login.tsx: POST the raw Telegram initData to the
 * Core API's `/auth/telegram/webapp` (`verify_telegram_webapp_auth`) path,
 * receive a session JWT, and stash it. RLS then scopes every later call to the
 * caller server-side (fail-closed) — the frontend never sends a user id.
 */
import type { Schemas } from "./client";
import { apiRequest } from "./client";
import { setSessionToken } from "./session";

type AuthResponse = Schemas["AuthResponse"];
type SessionIdentity = Schemas["SessionIdentity"];

/**
 * Exchange Telegram initData for a session JWT and store it.
 *
 * @param initData - the raw `WebApp.initData` query string.
 * @returns the session identity claims for the authenticated caller.
 * @throws {ApiError} when verification fails (401) or the network is down.
 */
export async function authenticateWithInitData(
    initData: string,
): Promise<SessionIdentity> {
    const res = await apiRequest<AuthResponse>("/auth/telegram/webapp", {
        method: "POST",
        body: { initData } satisfies Schemas["TelegramWebAppAuthRequest"],
        anonymous: true,
    });
    setSessionToken(res.token);
    return res.user;
}
