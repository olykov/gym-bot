import { useState, useEffect } from 'react';
import { useSession, signIn } from 'next-auth/react';
import { 
  isInTelegram, 
  getTelegramUser, 
  hasValidTelegramAuth,
  convertTelegramUserToAuth 
} from '../lib/telegram-mini-app';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  isTelegramMiniApp: boolean;
  autoAuthAttempted: boolean;
  error: string | null;
}

/**
 * Enhanced authentication hook with Telegram Mini App support
 * 
 * This hook:
 * 1. Detects if running in Telegram Mini App
 * 2. Auto-authenticates users from Telegram
 * 3. Falls back to manual authentication for external users
 */
export const useEnhancedAuth = () => {
  const { data: session, status } = useSession();
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    isTelegramMiniApp: false,
    autoAuthAttempted: false,
    error: null
  });

  useEffect(() => {
    initializeAuth();
  }, []);

  useEffect(() => {
    // Update auth state when session changes
    if (status === 'authenticated') {
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: true,
        isLoading: false,
        error: null
      }));
    } else if (status === 'unauthenticated') {
      setAuthState(prev => ({
        ...prev,
        isAuthenticated: false,
        isLoading: prev.autoAuthAttempted ? false : prev.isLoading
      }));
    }
  }, [status, session]);

  const initializeAuth = async () => {
    console.log('🔐 Initializing enhanced authentication...');
    
    const isMiniApp = isInTelegram();
    
    setAuthState(prev => ({
      ...prev,
      isTelegramMiniApp: isMiniApp,
      isLoading: true
    }));

    if (isMiniApp && hasValidTelegramAuth()) {
      console.log('📱 Telegram Mini App detected - attempting auto-authentication');
      await attemptAutoAuth();
    } else {
      console.log('🌐 External access detected - manual authentication required');
      setAuthState(prev => ({
        ...prev,
        autoAuthAttempted: true,
        isLoading: false
      }));
    }
  };

  const attemptAutoAuth = async () => {
    try {
      const telegramUser = getTelegramUser();
      
      if (!telegramUser) {
        throw new Error('No Telegram user data found');
      }

      console.log(`👤 Auto-authenticating user: ${telegramUser.first_name} (@${telegramUser.username})`);

      // Convert Telegram user data to our auth format
      const authData = convertTelegramUserToAuth(telegramUser);

      // Sign in using our Telegram provider
      const result = await signIn('telegram', {
        ...authData,
        redirect: false
      });

      if (result?.error) {
        console.error('❌ Auto-authentication failed:', result.error);
        setAuthState(prev => ({
          ...prev,
          error: 'Auto-authentication failed',
          autoAuthAttempted: true,
          isLoading: false
        }));
      } else {
        console.log('✅ Auto-authentication successful');
        // Session will be updated via useEffect above
      }

    } catch (error) {
      console.error('❌ Auto-authentication error:', error);
      setAuthState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Auto-authentication failed',
        autoAuthAttempted: true,
        isLoading: false
      }));
    }
  };

  const manualLogin = async () => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
      
      if (authState.isTelegramMiniApp) {
        // In Mini App, try auto-auth again
        await attemptAutoAuth();
      } else {
        // External access - this will be handled by the TelegramLogin component
        console.log('🔄 Manual login will be handled by TelegramLogin component');
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    } catch (error) {
      console.error('❌ Manual login error:', error);
      setAuthState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false
      }));
    }
  };

  const logout = async () => {
    // Handle logout if needed
    console.log('👋 User logged out');
  };

  return {
    // Auth state
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    isTelegramMiniApp: authState.isTelegramMiniApp,
    autoAuthAttempted: authState.autoAuthAttempted,
    error: authState.error,
    
    // Session data
    session,
    
    // Actions
    manualLogin,
    logout,
    
    // Utilities
    shouldShowLogin: !authState.isAuthenticated && authState.autoAuthAttempted,
    canAutoAuth: authState.isTelegramMiniApp && hasValidTelegramAuth() && !authState.autoAuthAttempted
  };
};
