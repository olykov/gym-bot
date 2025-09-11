import NextAuth from 'next-auth';
import { authConfig } from '../../../lib/auth';

/**
 * NextAuth.js API handler with Telegram authentication
 */
export default NextAuth(authConfig);
