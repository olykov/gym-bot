/**
 * Session JWT store (spec §4).
 *
 * The token lives in memory for the session and is mirrored to sessionStorage
 * so a viewport reload inside Telegram keeps the session without re-auth. It is
 * NEVER persisted to localStorage (Mini App sessions are short-lived) and never
 * embedded anywhere the frontend would leak it.
 */
const SESSION_KEY = "gym_web_jwt";

let inMemoryToken: string | null = null;

export function setSessionToken(token: string): void {
    inMemoryToken = token;
    try {
        sessionStorage.setItem(SESSION_KEY, token);
    } catch {
        /* sessionStorage may be unavailable; memory copy still works */
    }
}

export function getSessionToken(): string | null {
    if (inMemoryToken) return inMemoryToken;
    try {
        inMemoryToken = sessionStorage.getItem(SESSION_KEY);
    } catch {
        inMemoryToken = null;
    }
    return inMemoryToken;
}

export function clearSessionToken(): void {
    inMemoryToken = null;
    try {
        sessionStorage.removeItem(SESSION_KEY);
    } catch {
        /* ignore */
    }
}
