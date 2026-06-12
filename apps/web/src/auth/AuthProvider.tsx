/**
 * Auth gate (spec §4): runs the initData -> JWT round-trip once on mount and
 * exposes the resulting status to the tree. While pending it shows a skeleton
 * shell; on failure it renders an ErrorState with retry. Children only mount
 * once a session exists, so every authed call has a token.
 */
import {
    createContext,
    useContext,
    useEffect,
    useState,
    type ReactNode,
} from "react";
import type { Schemas } from "@/api/client";
import { ApiError } from "@/api/client";
import { t } from "@/i18n/catalog";
import { authenticateWithInitData } from "@/api/auth";
import { getInitData, isTelegramEnv } from "@/telegram/webapp";

type SessionIdentity = Schemas["SessionIdentity"];

type AuthStatus = "pending" | "authed" | "error" | "no-telegram";

interface AuthContextValue {
    status: AuthStatus;
    identity: SessionIdentity | null;
    error: string | null;
    retry: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// The companion hook lives next to its provider on purpose (one auth module);
// editing this file simply falls back to a full reload instead of fast refresh.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
    return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [status, setStatus] = useState<AuthStatus>("pending");
    const [identity, setIdentity] = useState<SessionIdentity | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);

    useEffect(() => {
        let cancelled = false;

        if (!isTelegramEnv()) {
            // Opened outside Telegram (e.g. local browser dev). Don't block the
            // shell — surface a clear state instead of a failed auth loop.
            setStatus("no-telegram");
            return;
        }

        setStatus("pending");
        setError(null);

        authenticateWithInitData(getInitData())
            .then((id) => {
                if (cancelled) return;
                setIdentity(id);
                setStatus("authed");
            })
            .catch((err: unknown) => {
                if (cancelled) return;
                // Server detail (4xx/5xx) passes through; the transport-level
                // status-0 "Network request failed" gets the localized
                // fallback so ru users never see a raw English string (GYM-109).
                const msg =
                    err instanceof ApiError && err.status !== 0
                        ? err.message
                        : t("auth.failed");
                setError(msg);
                setStatus("error");
            });

        return () => {
            cancelled = true;
        };
    }, [attempt]);

    const retry = () => setAttempt((n) => n + 1);

    return (
        <AuthContext.Provider value={{ status, identity, error, retry }}>
            {children}
        </AuthContext.Provider>
    );
}
