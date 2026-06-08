import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        // ECharts lives in its own async chunk (GYM-45); the main bundle is
        // ~373 kB. Raise the limit past the echarts chunk so the warning
        // targets only genuinely unintentional bloat, not this known split.
        chunkSizeWarningLimit: 1100,
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
