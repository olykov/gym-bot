import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/router';
import Header from '../components/Header';
import MuscleSetsChart from '../components/MuscleSetsChart';

interface MuscleSetsSeries {
  name: string;
  data: number[];
}

interface MuscleSetsWeeklyData {
  weeks: string[];
  series: MuscleSetsSeries[];
}

const SetsDistributionPage: React.FC = () => {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [muscleSetsData, setMuscleSetsData] = useState<MuscleSetsWeeklyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
      return;
    }
    
    if (status === 'authenticated' && session) {
      fetchFullMuscleSetsData();
    }
  }, [session, status, router]);

  const fetchFullMuscleSetsData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/muscle-sets-weekly-full');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🏋️ Full muscle sets fetch failed:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data: MuscleSetsWeeklyData = await response.json();
      console.log(`📊 Loaded full muscle sets data: ${data.series.length} muscles, ${data.weeks.length} weeks`);
      setMuscleSetsData(data);
    } catch (err) {
      console.error('📊 Full muscle sets data error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load sets distribution data');
    } finally {
      setLoading(false);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">Loading sets distribution...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-6">
          <div className="text-lg text-red-600 mb-4">Error: {error}</div>
          <Link href="/profile" className="text-blue-600 hover:text-blue-800">
            ← Back to Profile
          </Link>
        </div>
      </div>
    );
  }

  if (!session?.user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Sets Distribution - Gym Progress Analytics</title>
        <meta name="description" content="Comprehensive sets distribution analysis across muscle groups" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Header 
        title="Gym Progress Analytics"
        subtitle="Sets Distribution Analysis"
      />

      <main className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header Section */}
        <div className="mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">
              Weekly Training Distribution
            </h2>
            <p className="text-gray-600">
              Complete overview of your training volume by muscle group over the last 12 months
            </p>
          </div>
        </div>

        {/* Orientation Hint */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-8">
          <div className="flex items-center">
            <svg className="w-4 h-4 text-blue-600 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-blue-700">
              For better viewing, rotate your device to landscape orientation.
            </p>
          </div>
        </div>

        {/* Chart Section */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          {!muscleSetsData || muscleSetsData.series.length === 0 ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p className="text-lg font-medium">No training data available</p>
                <p className="text-sm mt-1">Start training to see your detailed sets distribution!</p>
              </div>
            </div>
          ) : (
            <MuscleSetsChart
              weeks={muscleSetsData.weeks}
              series={muscleSetsData.series}
              title="Weekly Training Distribution"
              height={600}
              showToolbox={true}
            />
          )}
        </div>

      </main>
    </div>
  );
};

export default SetsDistributionPage;