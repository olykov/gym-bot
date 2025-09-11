import { AuthDataValidator } from '@telegram-auth/server';
import { objectToAuthDataMap } from '@telegram-auth/server/utils';
import type { TelegramUser } from '../types';

/**
 * Validates Telegram authentication data using the bot token
 */
export class TelegramAuthValidator {
  private validator: AuthDataValidator;

  constructor(botToken: string) {
    this.validator = new AuthDataValidator({ 
      botToken,
      inValidateDataAfter: 86400 // 24 hours
    });
  }

  /**
   * Validates Telegram auth data and returns user information
   */
  async validateAuthData(authData: Record<string, string | number>): Promise<TelegramUser> {
    try {
      // Convert the auth data to the format expected by the validator
      const authDataMap = objectToAuthDataMap(authData);
      
      // Validate the data using the Telegram auth validator
      const validatedUser = await this.validator.validate<TelegramUser>(authDataMap);
      
      return validatedUser;
    } catch (error) {
      console.error('Telegram auth validation failed:', error);
      throw new Error('Invalid Telegram authentication data');
    }
  }
}

/**
 * Creates a singleton instance of the Telegram validator
 */
let validatorInstance: TelegramAuthValidator | null = null;

export function getTelegramValidator(): TelegramAuthValidator {
  if (!validatorInstance) {
    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    if (!botToken) {
      throw new Error('TELEGRAM_BOT_TOKEN environment variable is required');
    }
    validatorInstance = new TelegramAuthValidator(botToken);
  }
  return validatorInstance;
}
