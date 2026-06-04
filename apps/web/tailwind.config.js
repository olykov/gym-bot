/** @type {import('tailwindcss').Config} */
// All colors/spacing/radii/shadows map to the CSS variables defined in
// src/styles/tokens.css (Telegram themeParams + the "Chalk & Iron" brand layer,
// spec §3 + §9.3). No magic numbers/colors live here — tokens only.
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        // Spacing scale is the ONLY sanctioned set (spec §3): 4/8/12/16/24/32.
        spacing: {
            0: "0px",
            1: "4px",
            2: "8px",
            3: "12px",
            4: "16px",
            6: "24px",
            8: "32px",
            // Shell chrome heights (used by header/nav + container padding).
            header: "var(--header-h)",
            nav: "var(--nav-h)",
        },
        extend: {
            colors: {
                bg: "var(--bg)",
                text: "var(--text)",
                hint: "var(--hint)",
                link: "var(--link)",
                button: "var(--button)",
                "button-text": "var(--button-text)",
                "secondary-bg": "var(--secondary-bg)",
                // App-owned brand layer (survives any Telegram theme).
                accent: "var(--accent)",
                "accent-weak": "var(--accent-weak)",
                hairline: "var(--hairline)",
            },
            maxWidth: {
                container: "var(--container-max)",
            },
            borderRadius: {
                sm: "var(--radius-sm)",
                DEFAULT: "var(--radius-md)",
                md: "var(--radius-md)",
                lg: "var(--radius-lg)",
                full: "9999px",
            },
            boxShadow: {
                card: "var(--shadow-card)",
            },
            fontFamily: {
                // Bebas Neue (display/numerals) + Sora (body/UI) — spec §9.2.
                display: "var(--font-display)",
                body: "var(--font-body)",
            },
            fontSize: {
                // Typographic scale — tokens only.
                label: ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.02em" }],
                base: ["0.9375rem", { lineHeight: "1.4rem" }],
                stat: ["2.5rem", { lineHeight: "1" }],
                "stat-lg": ["3.25rem", { lineHeight: "1" }],
                title: ["1.5rem", { lineHeight: "1.5rem", letterSpacing: "0.01em" }],
            },
            transitionTimingFunction: {
                "out-soft": "cubic-bezier(0.16, 1, 0.3, 1)",
            },
        },
    },
    plugins: [],
}
