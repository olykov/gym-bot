/**
 * 🔒 REUSABLE TELEGRAM AUTHENTICATION MODULE
 * 
 * This module provides a complete Telegram authentication solution for Next.js applications.
 * It can be easily copied to other projects for instant Telegram login functionality.
 * 
 * Features:
 * - Server-side Telegram data validation
 * - JWT-based sessions (no database required)
 * - TypeScript support
 * - NextAuth.js integration
 * 
 * Usage in other projects:
 * 1. Copy this entire lib/auth/ folder
 * 2. Install dependencies: @telegram-auth/react, @telegram-auth/server, next-auth
 * 3. Set environment variables: TELEGRAM_BOT_TOKEN, NEXTAUTH_SECRET
 * 4. Use authConfig in your NextAuth setup
 */

import { TelegramProvider as Provider } from './telegram-provider';
import { authConfig as config } from './auth-config';

export { Provider as TelegramProvider };
export { getTelegramValidator, TelegramAuthValidator } from './telegram-validator';
export { config as authConfig };

// Type exports for external usage
export type { TelegramUser } from '../types';

/**
 * Complete auth configuration for easy integration
 */
export const TelegramAuth = {
  provider: Provider,
  config: config,
};

export default TelegramAuth;
