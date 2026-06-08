/**
 * Device timezone — resolved once at module load time.
 *
 * Uses the IANA timezone name reported by the JS runtime (reliable in all
 * modern browsers and Telegram WebView, e.g. "Asia/Tbilisi", "Europe/Kyiv").
 * Exported as a plain string constant so it is computed exactly once and
 * shared by every hook that needs to send `tz` to the API.
 *
 * If the runtime cannot resolve a timezone (rare edge case — some sandboxed
 * environments return "" or undefined), the export is `undefined` and callers
 * MUST omit the `tz` param entirely so the server falls back to UTC.
 */
const raw: string | undefined =
    Intl.DateTimeFormat().resolvedOptions().timeZone;

export const DEVICE_TZ: string | undefined =
    raw && raw.length > 0 ? raw : undefined;
