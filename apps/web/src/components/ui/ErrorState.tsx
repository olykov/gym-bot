/**
 * The ONE inline error surface (spec §10.4): a Sora message + a retry that
 * re-runs the query. No raw error dumps in the client UI.
 */
interface ErrorStateProps {
    message?: string;
    onRetry?: () => void;
}

export function ErrorState({
    message = "Something went wrong.",
    onRetry,
}: ErrorStateProps) {
    return (
        <div className="flex flex-col items-center px-4 py-8 text-center">
            <p className="max-w-[40ch] text-base text-text">❌ {message}</p>
            {onRetry ? (
                <button
                    type="button"
                    onClick={onRetry}
                    className="press-95 mt-4 min-h-[44px] rounded-md bg-accent-weak px-6 text-base font-semibold text-accent"
                >
                    Try again
                </button>
            ) : null}
        </div>
    );
}
