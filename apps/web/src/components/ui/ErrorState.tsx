/**
 * The ONE inline error surface (spec §10.4): a Sora message + a retry that
 * re-runs the query. No raw error dumps in the client UI.
 *
 * GYM-123 #4: the leading mark is a token-stroked inline SVG (circle + X in
 * --accent — graphical accent use, a11y-OK per §9.3), not an emoji, so the
 * surface stays on-brand in both themes.
 */
import { useT } from "@/i18n/catalog";

interface ErrorStateProps {
    message?: string;
    onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
    const { t } = useT();
    return (
        <div className="flex flex-col items-center px-4 py-8 text-center">
            <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
                className="mb-2 shrink-0"
            >
                <circle
                    cx="12"
                    cy="12"
                    r="9"
                    stroke="var(--accent)"
                    strokeWidth="2"
                />
                <path
                    d="M9 9l6 6M15 9l-6 6"
                    stroke="var(--accent)"
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </svg>
            <p className="max-w-[40ch] text-base text-text">
                {message ?? t("error.generic")}
            </p>
            {onRetry ? (
                <button
                    type="button"
                    onClick={onRetry}
                    className="press-95 mt-4 min-h-[44px] rounded-md bg-accent-weak px-6 text-base font-semibold text-accent"
                >
                    {t("common.retry")}
                </button>
            ) : null}
        </div>
    );
}
