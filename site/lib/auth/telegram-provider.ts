import type { CredentialsConfig } from 'next-auth/providers/credentials';
import type { TelegramUser } from '../types';
import { getTelegramValidator } from './telegram-validator';

/**
 * Custom Telegram provider for NextAuth.js
 * Validates Telegram authentication data and creates user sessions
 */
export const TelegramProvider: CredentialsConfig = {
  id: 'telegram',
  name: 'Telegram',
  type: 'credentials',
  credentials: {
    auth_date: { label: 'Auth Date', type: 'text' },
    first_name: { label: 'First Name', type: 'text' },
    hash: { label: 'Hash', type: 'text' },
    id: { label: 'ID', type: 'text' },
    last_name: { label: 'Last Name', type: 'text' },
    photo_url: { label: 'Photo URL', type: 'text' },
    username: { label: 'Username', type: 'text' },
  },
  
  async authorize(credentials) {
    try {
      if (!credentials) {
        throw new Error('No credentials provided');
      }

      // Prepare auth data for validation
      const authData: Record<string, string | number> = {
        auth_date: parseInt(credentials.auth_date as string),
        first_name: credentials.first_name as string,
        hash: credentials.hash as string,
        id: parseInt(credentials.id as string),
      };

      // Add optional fields if present
      if (credentials.last_name) {
        authData.last_name = credentials.last_name as string;
      }
      if (credentials.photo_url) {
        authData.photo_url = credentials.photo_url as string;
      }
      if (credentials.username) {
        authData.username = credentials.username as string;
      }

      // Validate the Telegram auth data
      const validator = getTelegramValidator();
      const validatedUser: TelegramUser = await validator.validateAuthData(authData);

      // Return user object for NextAuth session
      return {
        id: validatedUser.id.toString(),
        name: validatedUser.first_name + (validatedUser.last_name ? ` ${validatedUser.last_name}` : ''),
        email: null, // Telegram doesn't provide email
        image: validatedUser.photo_url || null,
        // Add custom fields
        telegramId: validatedUser.id,
        telegramUsername: validatedUser.username || null,
        firstName: validatedUser.first_name,
        lastName: validatedUser.last_name || null,
      };
    } catch (error) {
      console.error('Telegram authorization failed:', error);
      return null;
    }
  },
};

export default TelegramProvider;
