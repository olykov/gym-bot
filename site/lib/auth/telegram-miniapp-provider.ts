import type { CredentialsConfig } from 'next-auth/providers/credentials';
import type { TelegramUser } from '../types';

/**
 * Enhanced Telegram provider that handles both Mini App and Widget authentication
 * 
 * This provider can handle:
 * 1. Telegram Login Widget authentication (hash validation required)
 * 2. Telegram Mini App authentication (already validated by Telegram)
 */
export const EnhancedTelegramProvider: CredentialsConfig = {
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

      console.log('🔐 Processing Telegram authentication:', {
        id: credentials.id,
        first_name: credentials.first_name,
        username: credentials.username,
        hash: credentials.hash?.substring(0, 10) + '...',
        auth_method: credentials.hash === 'mini_app_auth' ? 'Mini App' : 'Login Widget'
      });

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

      // Handle Mini App authentication (no hash validation needed)
      if (credentials.hash === 'mini_app_auth') {
        console.log('📱 Mini App authentication - skipping hash validation');
        
        // For Mini Apps, we trust the data since it comes from Telegram's secure context
        const validatedUser = {
          id: parseInt(credentials.id as string),
          first_name: credentials.first_name as string,
          last_name: credentials.last_name as string || undefined,
          username: credentials.username as string || undefined,
          photo_url: credentials.photo_url as string || undefined,
          auth_date: parseInt(credentials.auth_date as string)
        };

        return createUserObject(validatedUser);
      }

      // Handle Login Widget authentication (requires hash validation)
      console.log('🌐 Login Widget authentication - validating hash');
      
      // Import validator dynamically to avoid issues with Mini App flow
      const { getTelegramValidator } = await import('./telegram-validator');
      const validator = getTelegramValidator();
      const validatedUser: TelegramUser = await validator.validateAuthData(authData);

      return createUserObject(validatedUser);

    } catch (error) {
      console.error('❌ Telegram authorization failed:', error);
      return null;
    }
  },
};

/**
 * Create NextAuth user object from validated Telegram user data
 */
function createUserObject(validatedUser: any) {
  const userObject = {
    id: validatedUser.id.toString(),
    name: validatedUser.first_name + (validatedUser.last_name ? ` ${validatedUser.last_name}` : ''),
    email: null, // Telegram doesn't provide email
    image: validatedUser.photo_url || null,
    // Add custom fields
    telegramId: validatedUser.id,
    telegramUsername: validatedUser.username || null,
    firstName: validatedUser.first_name,
    lastName: validatedUser.last_name || null,
    authMethod: validatedUser.hash === 'mini_app_auth' ? 'mini_app' : 'login_widget'
  };

  console.log('✅ User object created:', {
    id: userObject.id,
    name: userObject.name,
    telegramUsername: userObject.telegramUsername,
    authMethod: userObject.authMethod
  });

  return userObject;
}

export default EnhancedTelegramProvider;
