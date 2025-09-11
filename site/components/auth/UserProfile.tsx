import React from 'react';
import Link from 'next/link';
import { useSession, signOut } from 'next-auth/react';

/**
 * User Profile Component
 * Displays logged-in user information and logout functionality
 */
const UserProfile: React.FC = () => {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-8 h-8 bg-gray-200 rounded-full animate-pulse"></div>
        <div className="w-24 h-4 bg-gray-200 rounded animate-pulse"></div>
      </div>
    );
  }

  if (!session?.user) {
    return null;
  }

  const user = session.user as any;

  const handleLogout = async () => {
    await signOut({ 
      callbackUrl: '/login',
      redirect: true 
    });
  };

  return (
    <div className="flex items-center space-x-3">
      {/* User Avatar - Clickable */}
      <Link href="/profile" className="flex-shrink-0">
        {user.image ? (
          <img
            src={user.image}
            alt={user.name || 'User'}
            className="w-10 h-10 rounded-full border-2 border-blue-200 hover:border-blue-400 transition-colors duration-200 cursor-pointer"
            title="View Profile"
          />
        ) : (
          <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold hover:bg-blue-600 transition-colors duration-200 cursor-pointer" title="View Profile">
            {user.firstName ? user.firstName.charAt(0).toUpperCase() : 'U'}
          </div>
        )}
      </Link>

      {/* User Info - Hidden on mobile */}
      <div className="flex-1 min-w-0 hidden md:block">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-900 truncate">
            {user.name || user.firstName || 'User'}
          </span>
          {user.telegramUsername && (
            <span className="text-xs text-blue-600">
              @{user.telegramUsername}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2 text-xs text-gray-500">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.374 0 0 5.373 0 12s5.374 12 12 12 12-5.373 12-12S18.626 0 12 0zm5.568 8.16c-.169 1.858-.896 6.728-.896 6.728-.379 2.655-.998 3.105-1.308 3.105-.783 0-.783-.671-.783-.671s.085-1.077.194-1.841c.136-.954.337-2.275.337-2.275s.707-4.386.707-6.523c0-.954-.465-1.107-.93-1.107s-.93.153-.93 1.107c0 2.137.707 6.523.707 6.523s.201 1.321.337 2.275c.109.764.194 1.841.194 1.841s0 .671-.783.671c-.31 0-.929-.45-1.308-3.105 0 0-.727-4.87-.896-6.728C8.925 7.067 8.925 4 12 4s3.075 3.067 2.568 4.16z"/>
          </svg>
          <span>Telegram User</span>
        </div>
      </div>

      {/* Logout Button */}
      <button
        onClick={handleLogout}
        className="flex-shrink-0 px-3 py-1 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors duration-200 hidden md:block"
        title="Logout"
      >
        Logout
      </button>

      {/* Mobile Logout Button - Icon only */}
      <button
        onClick={handleLogout}
        className="flex-shrink-0 p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-full transition-colors duration-200 md:hidden"
        title="Logout"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
      </button>
    </div>
  );
};

export default UserProfile;
