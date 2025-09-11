/**
 * 🚀 Telegram Mini App Integration
 * 
 * This module provides utilities for seamless integration with Telegram Mini Apps.
 * It automatically detects when users are accessing from within Telegram and
 * extracts their authentication data without requiring manual login.
 */

// Telegram Web App API interfaces
interface TelegramWebAppUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

interface TelegramWebAppInitData {
  user?: TelegramWebAppUser;
  start_param?: string;
  query_id?: string;
  auth_date?: number;
  hash?: string;
}

interface TelegramMainButton {
  text: string;
  isVisible: boolean;
  onClick: (callback: () => void) => void;
  offClick: (callback: () => void) => void;
  show: () => void;
  hide: () => void;
  setText: (text: string) => void;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: TelegramWebAppInitData;
  ready: () => void;
  expand: () => void;
  close: () => void;
  MainButton: TelegramMainButton;
  onEvent: (eventType: string, callback: () => void) => void;
  offEvent: (eventType: string, callback: () => void) => void;
  sendData: (data: string) => void;
  openLink: (url: string) => void;
  colorScheme: 'light' | 'dark';
  viewportHeight: number;
  isExpanded: boolean;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

/**
 * Check if the app is running inside Telegram
 */
export const isInTelegram = (): boolean => {
  return typeof window !== 'undefined' && !!window.Telegram?.WebApp;
};

/**
 * Initialize Telegram Web App and return the interface
 */
export const initTelegramApp = (): TelegramWebApp | null => {
  if (isInTelegram()) {
    const WebApp = window.Telegram!.WebApp;
    
    // Initialize the app
    WebApp.ready();
    WebApp.expand();
    
    return WebApp;
  }
  
  // For development outside of Telegram, create a mock
  if (process.env.NODE_ENV === 'development') {
    return createMockTelegramWebApp();
  }
  
  return null;
};

/**
 * Get user data from Telegram Web App
 */
export const getTelegramUser = (): TelegramWebAppUser | null => {
  const WebApp = initTelegramApp();
  return WebApp?.initDataUnsafe?.user || null;
};

/**
 * Get the raw init data string for server-side validation
 */
export const getTelegramInitData = (): string => {
  const WebApp = initTelegramApp();
  return WebApp?.initData || '';
};

/**
 * Create a mock Telegram WebApp for development
 */
const createMockTelegramWebApp = (): TelegramWebApp => {
  console.log('🔧 Development mode: Using mock Telegram Web App');
  
  return {
    initData: 'query_id=mock_query&user=%7B%22id%22%3A987654321%2C%22first_name%22%3A%22Dev%22%2C%22last_name%22%3A%22User%22%2C%22username%22%3A%22devuser%22%2C%22language_code%22%3A%22en%22%7D&auth_date=1640995200&hash=mock_hash',
    initDataUnsafe: {
      user: {
        id: 987654321,
        first_name: 'Dev',
        last_name: 'User',
        username: 'devuser',
        language_code: 'en',
        photo_url: 'https://via.placeholder.com/150'
      },
      start_param: '',
      query_id: 'mock_query',
      auth_date: 1640995200,
      hash: 'mock_hash'
    },
    ready: () => console.log('📱 Mock WebApp ready'),
    expand: () => console.log('📱 Mock WebApp expanded'),
    close: () => console.log('📱 Mock WebApp closed'),
    MainButton: {
      text: 'CONTINUE',
      isVisible: false,
      onClick: (callback) => {
        console.log('📱 Mock MainButton.onClick registered');
      },
      offClick: (callback) => {
        console.log('📱 Mock MainButton.offClick registered');
      },
      show: () => {
        console.log('📱 Mock MainButton shown');
      },
      hide: () => {
        console.log('📱 Mock MainButton hidden');
      },
      setText: (text) => {
        console.log(`📱 Mock MainButton text set to: ${text}`);
      }
    },
    onEvent: (eventType, callback) => {
      console.log(`📱 Mock Event ${eventType} registered`);
    },
    offEvent: (eventType, callback) => {
      console.log(`📱 Mock Event ${eventType} unregistered`);
    },
    sendData: (data) => {
      console.log(`📱 Mock Data sent: ${data}`);
    },
    openLink: (url) => {
      console.log(`📱 Mock Link opened: ${url}`);
    },
    colorScheme: 'light',
    viewportHeight: 600,
    isExpanded: true
  };
};

/**
 * Show Telegram MainButton with custom text
 */
export const showMainButton = (text: string, callback: () => void) => {
  const WebApp = initTelegramApp();
  if (WebApp) {
    WebApp.MainButton.setText(text);
    WebApp.MainButton.onClick(callback);
    WebApp.MainButton.show();
  }
};

/**
 * Hide Telegram MainButton
 */
export const hideMainButton = () => {
  const WebApp = initTelegramApp();
  if (WebApp) {
    WebApp.MainButton.hide();
  }
};

/**
 * Send data back to Telegram Bot
 */
export const sendDataToTelegramBot = (data: string) => {
  const WebApp = initTelegramApp();
  if (WebApp) {
    WebApp.sendData(data);
  }
};

/**
 * Check if user has valid Telegram authentication data
 */
export const hasValidTelegramAuth = (): boolean => {
  const user = getTelegramUser();
  return !!(user && user.id && user.first_name);
};

/**
 * Get Telegram theme (light/dark)
 */
export const getTelegramTheme = (): 'light' | 'dark' => {
  const WebApp = initTelegramApp();
  return WebApp?.colorScheme || 'light';
};

/**
 * Convert Telegram user to our auth format
 */
export const convertTelegramUserToAuth = (telegramUser: TelegramWebAppUser) => {
  return {
    id: telegramUser.id.toString(),
    first_name: telegramUser.first_name,
    last_name: telegramUser.last_name || '',
    username: telegramUser.username || '',
    photo_url: telegramUser.photo_url || '',
    auth_date: Math.floor(Date.now() / 1000),
    hash: 'mini_app_auth' // Will be validated differently for Mini Apps
  };
};

export type { TelegramWebAppUser, TelegramWebApp, TelegramWebAppInitData };
