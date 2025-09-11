import type { NextAuthOptions } from 'next-auth';
import { EnhancedTelegramProvider } from './telegram-miniapp-provider';

/**
 * NextAuth.js configuration with enhanced Telegram authentication
 * Supports both Mini App and Login Widget authentication
 */
export const authConfig: NextAuthOptions = {
  providers: [EnhancedTelegramProvider],
  
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },

  jwt: {
    maxAge: 24 * 60 * 60, // 24 hours
  },

  callbacks: {
    async jwt({ token, user }) {
      // Add user data to JWT token on sign in
      if (user) {
        token.telegramId = (user as any).telegramId;
        token.telegramUsername = (user as any).telegramUsername;
        token.firstName = (user as any).firstName;
        token.lastName = (user as any).lastName;
        token.authMethod = (user as any).authMethod; // Track how user authenticated
      }
      return token;
    },

    async session({ session, token }) {
      // Add custom fields to session
      if (token && session.user) {
        (session.user as any).id = token.sub;
        (session.user as any).telegramId = token.telegramId;
        (session.user as any).telegramUsername = token.telegramUsername;
        (session.user as any).firstName = token.firstName;
        (session.user as any).lastName = token.lastName;
        (session.user as any).authMethod = token.authMethod;
      }
      return session;
    },
  },

  pages: {
    signIn: '/login',
    error: '/login',
  },

  secret: process.env.NEXTAUTH_SECRET,
};

export default authConfig;
