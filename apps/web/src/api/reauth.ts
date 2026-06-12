/**
 * 401 self-heal (GYM-125 #1, review doc 02 §5).
 *
 * The session JWT is mirrored to sessionStorage (see ./session) and can
 * outlive its server-side expiry — every authed call then 401s and the app
 * showed endless ErrorStates. When that happens, apiRequest clears the stale
 * token, re-runs the initData→JWT exchange ONCE via this module, and retries
 * the original request once.
 *
 * Single-flight: concurrent 401s (several queries firing together) share one
 * in-flight exchange, so parallel retries never stampede the auth endpoint.
 * Outside Telegram there is no initData to exchange — re-auth is impossible,
 * so this returns false immediately and the caller surfaces the original 401
 * (no retry loop).
 */
import { authenticateWithInitData } from "./auth";
import { clearSessionToken } from "./session";
import { getInitData } from "@/telegram/webapp";

let inFlight: Promise<boolean> | null = null;

/**
 * Drop the stale session token and exchange initData for a fresh JWT.
 *
 * @returns true when a fresh token was stored (the caller may retry once);
 *          false when re-auth is impossible (no initData) or the exchange
 *          itself failed.
 */
export function reauthenticate(): Promise<boolean> {
    if (inFlight) return inFlight;
    const initData = getInitData();
    if (!initData) return Promise.resolve(false);
    clearSessionToken();
    inFlight = authenticateWithInitData(initData)
        .then(() => true)
        .catch(() => false)
        .finally(() => {
            inFlight = null;
        });
    return inFlight;
}
