import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useEnhancedAuth } from '../hooks/useEnhancedAuth';
import AutoAuth from '../components/auth/AutoAuth';
import TelegramMiniAppDashboard from '../components/TelegramMiniAppDashboard';

export default function Home() {
  const { 
    isAuthenticated, 
    isLoading, 
    session,
    isTelegramMiniApp
  } = useEnhancedAuth();
  
  const router = useRouter();

  useEffect(() => {
    // Redirect authenticated users to profile page
    if (isAuthenticated && !isLoading) {
      router.replace('/profile');
    }
  }, [isAuthenticated, isLoading, router]);

  // For Telegram Mini App users - always show the dashboard, even during auth
  if (isTelegramMiniApp) {
    return <TelegramMiniAppDashboard session={session} isLoading={isLoading} />;
  }

  // For external users - show loading during auth
  if (isLoading) {
    return <AutoAuth />;
  }

  // For external users - redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Please login to view your gym progress</p>
          <a href="/login" className="text-blue-600 hover:text-blue-700 underline">
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  // This should not be reached since authenticated users are redirected to profile
  return null;
}
