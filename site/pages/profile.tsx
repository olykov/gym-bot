import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/router';
import ActivityGrid from '../components/ActivityGrid';
import Header from '../components/Header';
import MuscleSetsChart from '../components/MuscleSetsChart';

interface DailyActivity {
  date: string;
  sets_count: number;
}

interface UserStats {
  totalTrainings: number;
  totalWeightLifted: number;
  activeDays: number;
  trainingsThisWeek: number;
  longestStreak: number;
  firstTrainingDate: string | null;
}

interface MuscleSetsSeries {
  name: string;
  data: number[];
}

interface MuscleSetsWeeklyData {
  weeks: string[];
  series: MuscleSetsSeries[];
}

interface UserActivityData {
  activityData: DailyActivity[];
  stats: UserStats;
}

const ProfilePage: React.FC = () => {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [activityData, setActivityData] = useState<UserActivityData | null>(null);
  const [muscleSetsData, setMuscleSetsData] = useState<MuscleSetsWeeklyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [muscleSetsLoading, setMuscleSetsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
      return;
    }
    
    if (status === 'authenticated' && session) {
      fetchUserActivity();
      fetchMuscleSetsData();
    }
  }, [session, status, router]);

  const fetchUserActivity = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/user-activity');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🏋️ User activity fetch failed:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data: UserActivityData = await response.json();
      console.log(`📊 Loaded activity data: ${data.activityData.length} days, ${data.stats.totalTrainings} trainings`);
      setActivityData(data);
    } catch (err) {
      console.error('📊 Activity data error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const fetchMuscleSetsData = async () => {
    try {
      setMuscleSetsLoading(true);
      const response = await fetch('/api/muscle-sets-weekly');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🏋️ Muscle sets fetch failed:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data: MuscleSetsWeeklyData = await response.json();
      console.log(`📊 Loaded muscle sets data: ${data.series.length} muscles, ${data.weeks.length} weeks`);
      setMuscleSetsData(data);
    } catch (err) {
      console.error('📊 Muscle sets data error:', err);
      // Don't set error state for muscle sets - it's not critical
    } finally {
      setMuscleSetsLoading(false);
    }
  };

  // Format large numbers for display
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  // Format weight with units
  const formatWeight = (weight: number): string => {
    return `${formatNumber(Math.round(weight))} kg`;
  };

  // Format member since date
  const formatMemberSince = (dateStr: string | null): string => {
    if (!dateStr) return new Date().getFullYear().toString();
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="text-lg text-red-600 mb-4">Error: {error}</div>
          <Link href="/" className="text-blue-600 hover:text-blue-800">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!session?.user || !activityData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">No data available</div>
      </div>
    );
  }

  const user = session.user as any;
  const { stats } = activityData;

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Profile - Gym Progress Analytics</title>
        <meta name="description" content="User profile and workout activity overview" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Header 
        title="Gym Progress Analytics"
        subtitle="User Profile"
      />

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* User Info Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <div className="flex flex-col sm:flex-row items-center sm:items-start space-y-4 sm:space-y-0 sm:space-x-6">
            {/* Large Avatar */}
            <div className="flex-shrink-0">
              {user.image ? (
                <img
                  src={user.image}
                  alt={user.firstName || 'User'}
                  className="w-24 h-24 rounded-full border-4 border-gray-200"
                />
              ) : (
                <div className="w-24 h-24 bg-gray-300 rounded-full flex items-center justify-center border-4 border-gray-200">
                  <span className="text-2xl text-gray-600">
                    {(user.firstName || 'U').charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
            </div>

            {/* User Details */}
            <div className="text-center sm:text-left">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {user.firstName} {user.lastName}
              </h1>
              <p className="text-lg text-gray-600 mb-1">
                @{user.telegramUsername}
              </p>
              <p className="text-sm text-gray-500">
                Member since {formatMemberSince(activityData?.stats.firstTrainingDate || null)}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row gap-3 justify-center sm:justify-start">
              <Link
                href="/exercises/chest/bench%20press"
                className="inline-flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200 font-medium"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                See Progress
              </Link>
              
              <button
                onClick={() => {}}
                className="inline-flex items-center justify-center px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors duration-200 font-medium"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Trainings
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards - 2x2 Grid */}
        <div className="grid grid-cols-2 gap-3 sm:gap-6 mb-8 max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 text-center">
            <div className="text-2xl sm:text-3xl font-bold text-blue-600 mb-1 sm:mb-2">
              {formatNumber(stats.totalTrainings)}
            </div>
            <div className="text-xs sm:text-sm text-gray-600">Training Days</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 text-center">
            <div className="text-2xl sm:text-3xl font-bold text-green-600 mb-1 sm:mb-2">
              {formatWeight(stats.totalWeightLifted)}
            </div>
            <div className="text-xs sm:text-sm text-gray-600">Weight Lifted</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 text-center">
            <div className="text-2xl sm:text-3xl font-bold text-purple-600 mb-1 sm:mb-2">
              {stats.activeDays}
            </div>
            <div className="text-xs sm:text-sm text-gray-600">Active Days</div>
            <div className="text-xs text-gray-500">(Last Year)</div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 text-center">
            <div className="text-2xl sm:text-3xl font-bold text-orange-600 mb-1 sm:mb-2">
              {stats.trainingsThisWeek}
            </div>
            <div className="text-xs sm:text-sm text-gray-600">This Week</div>
            <div className="text-xs text-gray-500">
              Best: {stats.longestStreak} days
            </div>
          </div>
        </div>

        {/* Activity Section */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              🏋️ Workout Activity
            </h2>
            <p className="text-gray-600">
              Your training intensity over the last year. Each square represents a day, 
              with darker colors indicating more sets completed.
            </p>
          </div>

          {/* Activity Grid */}
          <div className="flex justify-center overflow-x-auto">
            <ActivityGrid activityData={activityData.activityData} />
          </div>

          {/* Activity Summary */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <div className="text-center text-sm text-gray-600">
              <p>
                <span className="font-medium text-gray-800">{stats.activeDays}</span> active days in the last year
              </p>
              <p className="mt-1">
                Keep up the great work! 💪
              </p>
            </div>
          </div>
        </div>

        {/* Muscle Sets Weekly Chart */}
        <div className="bg-white rounded-lg shadow-lg p-8 mt-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              📈 Weekly Training Distribution
            </h2>
            <p className="text-gray-600">
              Sets count by muscle group over the last 12 months. 
              Each color represents a different muscle group trained.
            </p>
          </div>

          {muscleSetsLoading ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-600">Loading weekly training data...</p>
              </div>
            </div>
          ) : muscleSetsData && muscleSetsData.series.length > 0 ? (
            <MuscleSetsChart
              weeks={muscleSetsData.weeks}
              series={muscleSetsData.series}
              height={400}
              showToolbox={true}
            />
          ) : (
            <div className="flex items-center justify-center h-96">
              <div className="text-center text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p className="text-lg font-medium">No training data available</p>
                <p className="text-sm mt-1">Start training to see your weekly muscle distribution!</p>
              </div>
            </div>
          )}

          {muscleSetsData && muscleSetsData.series.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200 text-center">
              <Link
                href="/sets-distribution"
                className="inline-flex items-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors duration-200 font-medium"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                See Full Graph
              </Link>
            </div>
          )}
        </div>

      </main>
    </div>
  );
};

export default ProfilePage;