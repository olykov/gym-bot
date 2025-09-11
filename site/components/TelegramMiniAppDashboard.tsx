import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { signIn } from 'next-auth/react';
import ExerciseProgressChart from './BenchPressChart';
import UserProfile from './auth/UserProfile';
import { getTelegramUser, convertTelegramUserToAuth } from '../lib/telegram-mini-app';

interface TelegramMiniAppDashboardProps {
  session: any;
  isLoading: boolean;
}

/**
 * Special dashboard component for Telegram Mini App users
 * Handles auto-authentication and shows dashboard immediately
 */
const TelegramMiniAppDashboard: React.FC<TelegramMiniAppDashboardProps> = ({ session, isLoading }) => {
  const [authAttempted, setAuthAttempted] = useState(false);
  const [telegramUser, setTelegramUser] = useState<any>(null);

  useEffect(() => {
    // Get Telegram user data immediately
    const user = getTelegramUser();
    if (user) {
      setTelegramUser(user);
      
      // If no session yet, attempt auto-authentication
      if (!session && !authAttempted) {
        attemptAutoAuth(user);
        setAuthAttempted(true);
      }
    }
  }, [session, authAttempted]);

  const attemptAutoAuth = async (user: any) => {
    try {
      console.log('📱 Auto-authenticating Mini App user:', user.first_name);
      
      const authData = convertTelegramUserToAuth(user);
      
      await signIn('telegram', {
        ...authData,
        redirect: false
      });
    } catch (error) {
      console.error('❌ Auto-auth failed:', error);
    }
  };

  // Show loading state during authentication
  if (!session && telegramUser) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            Welcome, {telegramUser.first_name}!
          </h1>
          
          <p className="text-gray-600 mb-2">
            🚀 Loading your gym progress...
          </p>
          
          <div className="mt-6 space-y-2">
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              <span>Authenticating via Telegram Mini App...</span>
            </div>
          </div>

          <div className="mt-8 flex items-center justify-center space-x-2 text-xs text-gray-400">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.374 0 0 5.373 0 12s5.374 12 12 12 12-5.373 12-12S18.626 0 12 0zm5.568 8.16c-.169 1.858-.896 6.728-.896 6.728-.379 2.655-.998 3.105-1.308 3.105-.783 0-.783-.671-.783-.671s.085-1.077.194-1.841c.136-.954.337-2.275.337-2.275s.707-4.386.707-6.523c0-.954-.465-1.107-.93-1.107s-.93.153-.93 1.107c0 2.137.707 6.523.707 6.523s.201 1.321.337 2.275c.109.764.194 1.841.194 1.841s0 .671-.783.671c-.31 0-.929-.45-1.308-3.105 0 0-.727-4.87-.896-6.728C8.925 7.067 8.925 4 12 4s3.075 3.067 2.568 4.16z"/>
            </svg>
            <span>Secured by Telegram</span>
          </div>
        </div>
      </div>
    );
  }

  // Show error state if no Telegram user found
  if (!telegramUser) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            Telegram Data Missing
          </h1>
          
          <p className="text-gray-600 mb-4">
            Unable to get user data from Telegram Mini App
          </p>
          
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Render the full dashboard once authenticated
  const user = session?.user as any;

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Gym Progress - Bench Press Analytics</title>
        <meta name="description" content="Personal bench press progress tracking for gym workouts" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header with User Profile */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-full">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Gym Progress Analytics</h1>
                <p className="text-sm text-gray-600">Telegram Mini App</p>
              </div>
            </div>
            
            {session ? (
              <UserProfile />
            ) : (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                <span>Authenticating...</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">
              Welcome back, {user?.firstName || telegramUser?.first_name || 'User'}!
            </h2>
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">
                <strong>Data Source:</strong> Telegram Gym Bot
              </p>
            </div>
          </div>
          
          <div className="w-full">
            <ExerciseProgressChart />
          </div>
          
          <div className="mt-8 border-t pt-6">
            <div className="text-center text-gray-500 text-sm">
              <p>Secure data from your Telegram Gym Bot training sessions</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TelegramMiniAppDashboard;
