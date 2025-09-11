import React, { useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useEnhancedAuth } from '../hooks/useEnhancedAuth';
import TelegramLogin from '../components/auth/TelegramLogin';
import AutoAuth from '../components/auth/AutoAuth';

/**
 * Smart Login Page Component
 * 
 * Handles both Telegram Mini App auto-authentication and external manual login:
 * - For Telegram Mini App users: Auto-authenticate seamlessly
 * - For external users: Show Telegram login widget
 */
const LoginPage: React.FC = () => {
  const router = useRouter();
  const { 
    isAuthenticated, 
    isLoading, 
    isTelegramMiniApp, 
    shouldShowLogin,
    canAutoAuth,
    error
  } = useEnhancedAuth();

  // Redirect to dashboard if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      console.log('✅ User authenticated - redirecting to dashboard');
      router.push('/');
    }
  }, [isAuthenticated, router]);

  // For Telegram Mini App users - redirect immediately to dashboard
  // They should never see the login page
  useEffect(() => {
    if (isTelegramMiniApp && !isAuthenticated && !isLoading) {
      console.log('📱 Mini App user detected - redirecting to dashboard');
      router.push('/');
    }
  }, [isTelegramMiniApp, isAuthenticated, isLoading, router]);

  // Show auto-auth component during loading or auto-auth process
  if (isLoading || canAutoAuth) {
    return <AutoAuth />;
  }

  // Don't render anything if already authenticated (prevents flash)
  if (isAuthenticated) {
    return null;
  }

  // If this is a Mini App user, don't show the login page
  if (isTelegramMiniApp) {
    return <AutoAuth />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Head>
        <title>Login - Gym Progress Analytics</title>
        <meta name="description" content="Login to access your personal gym progress analytics" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="max-w-md w-full">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Gym Progress Analytics
            </h1>
            <p className="text-gray-600">
              {isTelegramMiniApp 
                ? 'Welcome from Telegram! Please authenticate to continue.' 
                : 'Access your personal bench press progress data'
              }
            </p>
            
            {/* Context-aware subtitle */}
            {error && (
              <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                Auto-authentication failed. Please try manual login.
              </div>
            )}
          </div>

          {/* Login Card */}
          <div className="bg-white rounded-lg shadow-lg p-8">
            <TelegramLogin />
          </div>

          {/* Footer */}
          <div className="text-center mt-8 text-sm text-gray-500">
            <p>
              {isTelegramMiniApp 
                ? 'Authenticated via Telegram Mini App' 
                : 'Secure authentication powered by Telegram'
              }
            </p>
            <div className="flex items-center justify-center mt-2 space-x-1">
              <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-green-600 font-medium">
                {isTelegramMiniApp ? 'Mini App Ready' : 'Secure & Private'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
