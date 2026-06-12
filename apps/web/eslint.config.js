/**
 * ESLint flat config for apps/web (GYM-124).
 *
 * Deliberately NOT type-checked mode (no projectService) — the recommended
 * presets keep `npm run lint` fast enough to gate CI on every push. Strictness
 * comes from `--max-warnings 0` in the npm script: every warning fails.
 */
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default tseslint.config(
    { ignores: ["dist", "node_modules"] },
    {
        files: ["src/**/*.{ts,tsx}"],
        extends: [js.configs.recommended, ...tseslint.configs.recommended],
        plugins: {
            "react-hooks": reactHooks,
            "react-refresh": reactRefresh,
        },
        rules: {
            // The two classic react-hooks rules. NOT the full v7 `recommended`
            // preset: its new compiler-powered rules (set-state-in-effect,
            // refs) flag 9 pre-existing, intentional seed/reset-effect sites
            // (AuthProvider, RecordSheet, SetLogger, BottomSheet, SetEditor,
            // Progress) — migrating those patterns is its own task, not this
            // tooling wave (GYM-124).
            "react-hooks/rules-of-hooks": "error",
            "react-hooks/exhaustive-deps": "warn",
            "react-refresh/only-export-components": [
                "warn",
                { allowConstantExport: true },
            ],
        },
    },
);
