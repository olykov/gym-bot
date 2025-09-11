import React, { useEffect } from 'react';
import { useEnhancedAuth } from '../../hooks/useEnhancedAuth';

/**
 * Auto-Authentication Component
 * 
 * This component handles automatic authentication for Telegram Mini App users.
 * It shows appropriate loading states and handles the authentication flow.
 */
const AutoAuth: React.FC = () => {
  const { 
    isAuthenticated, 
    isLoading, 
    isTelegramMiniApp, 
    autoAuthAttempted,
    error,
    canAutoAuth
  } = useEnhancedAuth();

  useEffect(() => {
    if (isAuthenticated) {
      console.log('✅ Auto-authentication successful - user will be redirected');
    }
  }, [isAuthenticated]);

  // Don't render anything if authentication is complete
  if (isAuthenticated) {
    return null;
  }

  // Show loading state during auto-authentication
  if (isLoading || canAutoAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          {/* Loading Animation */}
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            Gym Progress Analytics
          </h1>

          {/* Status Message */}
          <div className="space-y-2">
            {isTelegramMiniApp ? (
              <>
                <p className="text-gray-600 mb-2">
                  🚀 Accessing from Telegram
                </p>
                <p className="text-sm text-blue-600 font-medium">
                  Authenticating automatically...
                </p>
              </>
            ) : (
              <>
                <p className="text-gray-600 mb-2">
                  🌐 External Access Detected
                </p>
                <p className="text-sm text-blue-600 font-medium">
                  Preparing login interface...
                </p>
              </>
            )}
          </div>

          {/* Progress Indicators */}
          <div className="mt-6 space-y-2">
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              <span>
                {isTelegramMiniApp 
                  ? 'Verifying Telegram authentication...' 
                  : 'Initializing secure login...'
                }
              </span>
            </div>
          </div>

          {/* Telegram Branding */}
          {isTelegramMiniApp && (
            <div className="mt-8 flex items-center justify-center space-x-2 text-xs text-gray-400">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.374 0 0 5.373 0 12s5.374 12 12 12 12-5.373 12-12S18.626 0 12 0zm5.568 8.16c-.169 1.858-.896 6.728-.896 6.728-.379 2.655-.998 3.105-1.308 3.105-.783 0-.783-.671-.783-.671s.085-1.077.194-1.841c.136-.954.337-2.275.337-2.275s.707-4.386.707-6.523c0-.954-.465-1.107-.93-1.107s-.93.153-.93 1.107c0 2.137.707 6.523.707 6.523s.201 1.321.337 2.275c.109.764.194 1.841.194 1.841s0 .671-.783.671c-.31 0-.929-.45-1.308-3.105 0 0-.727-4.87-.896-6.728C8.925 7.067 8.925 4 12 4s3.075 3.067 2.568 4.16z"/>
              </svg>
              <span>Secured by Telegram</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Show error state if auto-authentication failed
  if (error && autoAuthAttempted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-100 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          {/* Error Icon */}
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>

          {/* Error Message */}
          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            Authentication Error
          </h1>
          <p className="text-gray-600 mb-4">
            {error}
          </p>

          {/* Retry Button */}
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

  // This component only handles loading and error states
  // If we reach here, something unexpected happened
  return null;
};

export default AutoAuth;
