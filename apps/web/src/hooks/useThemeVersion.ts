/**
 * A version counter that bumps on Telegram `themeChanged` (spec §10.5).
 *
 * Components that read live CSS variables imperatively (the ECharts theme) can't
 * observe a CSS-var change on their own. They depend on this counter so they
 * re-read the vars and re-theme when Telegram flips light/dark. Outside Telegram
 * the listener is a harmless no-op.
 */
import { useEffect, useState } from "react";
import WebApp from "@twa-dev/sdk";

export function useThemeVersion(): number {
    const [version, setVersion] = useState(0);

    useEffect(() => {
        const bump = () => setVersion((v) => v + 1);
        WebApp.onEvent("themeChanged", bump);
        return () => WebApp.offEvent("themeChanged", bump);
    }, []);

    return version;
}
