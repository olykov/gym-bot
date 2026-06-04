/**
 * App root: providers + router (spec §1, §4).
 *
 * Order: TanStack Query (server-state cache for every API read) wraps the Auth
 * round-trip (initData -> JWT), which gates the routed shell. Routes mount
 * inside the one <AppShell>; "/" redirects to the Dashboard tab.
 */
import { useEffect } from "react";
import {
    createBrowserRouter,
    Navigate,
    RouterProvider,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { initTelegram } from "@/telegram/webapp";
import { AuthProvider } from "@/auth/AuthProvider";
import { AuthGate } from "@/auth/AuthGate";
import { AppShell } from "@/components/shell/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { Progress } from "@/pages/Progress";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Cache aggressively; never re-fetch on every mount (spec §1).
            staleTime: 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});

const router = createBrowserRouter([
    {
        path: "/",
        element: <AppShell />,
        children: [
            { index: true, element: <Navigate to="/dashboard" replace /> },
            { path: "dashboard", element: <Dashboard /> },
            { path: "progress", element: <Progress /> },
            { path: "*", element: <Navigate to="/dashboard" replace /> },
        ],
    },
]);

export default function App() {
    // Boot Telegram once: ready/expand + theme/viewport listeners (spec §4).
    useEffect(() => initTelegram(), []);

    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <AuthGate>
                    <RouterProvider router={router} />
                </AuthGate>
            </AuthProvider>
        </QueryClientProvider>
    );
}
