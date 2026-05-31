import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken, isAuthenticated } from '@/utils/auth';
import axios from 'axios';

import { API_URL } from '../config';
const TELEGRAM_BOT_USERNAME = 'olykov_gym_bot';

declare global {
    interface Window {
        TelegramLoginWidget: any;
        Telegram?: {
            WebApp?: {
                initData: string;
                initDataUnsafe: {
                    user?: {
                        id: number;
                        first_name: string;
                        last_name?: string;
                        username?: string;
                        photo_url?: string;
                    };
                    auth_date?: number;
                    hash?: string;
                };
            };
        };
    }
}

function Login() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [isTelegramWebApp, setIsTelegramWebApp] = useState(false);

    const [debugInfo, setDebugInfo] = useState<any>(null);

    useEffect(() => {
        // Redirect if already authenticated
        if (isAuthenticated()) {
            navigate('/');
            return;
        }

        // Check if opened as Telegram Mini App
        const telegramWebApp = window.Telegram?.WebApp;
        if (telegramWebApp && telegramWebApp.initData) {
            setIsTelegramWebApp(true);
            // Auto-login with Telegram WebApp data
            handleTelegramWebAppLogin(telegramWebApp.initData);
            return;
        }

        // Load Telegram Login Widget script for web browser
        const script = document.createElement('script');
        script.src = 'https://telegram.org/js/telegram-widget.js?22';
        script.setAttribute('data-telegram-login', TELEGRAM_BOT_USERNAME);
        script.setAttribute('data-size', 'large');
        script.setAttribute('data-radius', '8');
        script.setAttribute('data-request-access', 'write');
        script.setAttribute('data-onauth', 'onTelegramAuth(user)');
        script.async = true;

        const container = document.getElementById('telegram-login-container');
        if (container) {
            container.appendChild(script);
        }

        // Define global callback for Telegram auth
        (window as any).onTelegramAuth = async (user: any) => {
            try {
                setLoading(true);
                setError('');

                const response = await axios.post(`${API_URL}/auth/telegram`, user);
                setToken(response.data.token);
                navigate('/');
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Telegram authentication failed');
            } finally {
                setLoading(false);
            }
        };

        return () => {
            delete (window as any).onTelegramAuth;
        };
    }, [navigate]);

    const handleTelegramWebAppLogin = async (initData: string) => {
        try {
            setLoading(true);
            setError('');

            // Send raw initData to backend for verification
            const response = await axios.post(`${API_URL}/auth/telegram/webapp`, {
                initData
            });

            setToken(response.data.token);

            // Redirect based on role
            const userRole = response.data.user.role || 'user';
            navigate(userRole === 'admin' ? '/' : '/my-training');
        } catch (err: any) {
            console.error('Telegram WebApp auth error:', err);
            setError(err.response?.data?.detail || 'Telegram authentication failed.');
            setLoading(false);
            // Keep isTelegramWebApp true to show debug info instead of login form
            setDebugInfo({
                error: err.message,
                response: err.response ? {
                    status: err.response.status,
                    data: err.response.data
                } : 'No response',
                apiUrl: API_URL,
                initData: initData
            });
        }
    };

    const handleAdminLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await axios.post(`${API_URL}/auth/admin`, {
                username,
                password
            });

            setToken(response.data.token);
            navigate('/');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    // Show loading state for Telegram WebApp auto-login
    if (isTelegramWebApp && loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Authenticating via Telegram...</p>
                </div>
            </div>
        );
    }

    if (debugInfo) {
        return (
            <div className="min-h-screen bg-red-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md overflow-hidden">
                    <h2 className="text-xl font-bold text-red-600 mb-4">Debug Info</h2>
                    <div className="text-xs font-mono bg-gray-100 p-4 rounded overflow-auto max-h-96">
                        <p className="font-bold">Error:</p>
                        <pre className="mb-2 text-red-500">{debugInfo.error}</pre>

                        <p className="font-bold">API URL:</p>
                        <pre className="mb-2">{debugInfo.apiUrl}</pre>

                        <p className="font-bold">Response:</p>
                        <pre className="mb-2">{JSON.stringify(debugInfo.response, null, 2)}</pre>

                        <p className="font-bold">Init Data:</p>
                        <pre>{JSON.stringify(debugInfo.initDataUnsafe, null, 2)}</pre>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-4 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Panel</h1>
                    <p className="text-gray-600">Sign in to continue</p>
                </div>

                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        {error}
                    </div>
                )}

                {!isTelegramWebApp && (
                    <>
                        {/* Telegram Login */}
                        <div className="mb-8">
                            <div className="text-center mb-4">
                                <p className="text-sm font-medium text-gray-700 mb-3">Login with Telegram</p>
                                <div id="telegram-login-container" className="flex justify-center"></div>
                            </div>
                        </div>

                        {/* Divider */}
                        <div className="relative mb-8">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-gray-300"></div>
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-4 bg-white text-gray-500">Or continue with</span>
                            </div>
                        </div>
                    </>
                )}

                {/* Admin Login Form */}
                <form onSubmit={handleAdminLogin} className="space-y-4">
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                            Username
                        </label>
                        <input
                            id="username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                            placeholder="admin"
                            disabled={loading}
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                            placeholder="••••••••"
                            disabled={loading}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? 'Signing in...' : 'Sign in'}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default Login;
