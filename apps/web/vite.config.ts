import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react(), tailwindcss()],
    build: {
        // ECharts lives in its own async chunk (GYM-45), tree-shaken to
        // ~520 kB via echarts/core (GYM-129). Keep the limit just past that
        // chunk so the warning targets only genuinely unintentional bloat.
        chunkSizeWarningLimit: 600,
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
            "@api-contract": path.resolve(
                __dirname,
                "../../packages/api-contract/clients/typescript"
            ),
        },
    },
    server: {
        host: true,
        port: 5174,
        allowedHosts: true,
        proxy: {
            // Mirror apps/admin: the Core API is reached under /api/v1.
            '/api': {
                target: 'http://admin_backend:8000',
                changeOrigin: true,
                secure: false,
            }
        }
    }
})
