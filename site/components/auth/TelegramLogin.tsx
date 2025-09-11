import React from 'react';
import { LoginButton } from '@telegram-auth/react';
import { signIn } from 'next-auth/react';

interface TelegramLoginProps {
  className?: string;
}

/**
 * Telegram Login Button Component
 * Uses @telegram-auth/react for the Telegram widget integration
 */
const TelegramLogin: React.FC<TelegramLoginProps> = ({ className = '' }) => {
  const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;

  if (!botUsername) {
    return (
      <div className={`text-red-600 p-4 border border-red-300 rounded-lg ${className}`}>
        Error: TELEGRAM_BOT_USERNAME not configured
      </div>
    );
  }

  const handleTelegramAuth = async (data: any) => {
    try {
      console.log('Telegram auth data received:', data);
      
      // Sign in using NextAuth with the Telegram data
      const result = await signIn('telegram', {
        auth_date: data.auth_date,
        first_name: data.first_name,
        hash: data.hash,
        id: data.id,
        last_name: data.last_name || '',
        photo_url: data.photo_url || '',
        username: data.username || '',
        redirect: false,
      });

      if (result?.error) {
        console.error('NextAuth sign in failed:', result.error);
        alert('Authentication failed. Please try again.');
      } else {
        // Redirect to dashboard on successful login
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Telegram authentication error:', error);
      alert('Authentication failed. Please try again.');
    }
  };

  return (
    <div className={`flex flex-col items-center space-y-4 ${className}`}>
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Login with Telegram
        </h2>
        <p className="text-gray-600 text-sm">
          Click the button below to authenticate with your Telegram account
        </p>
      </div>
      
      <div className="telegram-login-widget">
        <LoginButton
          botUsername={botUsername}
          onAuthCallback={handleTelegramAuth}
          buttonSize="large"
          cornerRadius={8}
          showAvatar={true}
          lang="en"
        />
      </div>
      
      <div className="text-xs text-gray-500 text-center max-w-md">
        <p>
          By logging in, you agree to use your Telegram account to access your personal gym progress data.
          Your privacy is protected - we only access basic profile information.
        </p>
      </div>
    </div>
  );
};

export default TelegramLogin;
