import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useSession } from 'next-auth/react';
import Head from 'next/head';
import Header from '../../../components/Header';
import ExerciseProgressChart from '../../../components/BenchPressChart';
import { decodeFromUrl } from '../../../lib/url-utils';

interface ExercisePageProps {
  muscle: string;
  exercise: string;
}

const ExercisePage: React.FC = () => {
  const router = useRouter();
  const { data: session, status } = useSession();
  const { muscle, exercise } = router.query;

  // Redirect unauthenticated users to login
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  // Show loading while checking authentication
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Loading...</h1>
          <p className="text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated
  if (status === 'unauthenticated') {
    return null; // Router will handle redirect
  }

  // Wait for router query to be ready
  if (!muscle || !exercise) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading exercise data...</div>
      </div>
    );
  }

  // Decode URL parameters using utility function
  const rawMuscle = Array.isArray(muscle) ? muscle[0] : muscle;
  const rawExercise = Array.isArray(exercise) ? exercise[0] : exercise;
  const muscleTitle = decodeFromUrl(rawMuscle);
  const exerciseTitle = decodeFromUrl(rawExercise);

  const user = session?.user as any;

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>{exerciseTitle} Progress - {muscleTitle} | Gym Analytics</title>
        <meta 
          name="description" 
          content={`Personal ${exerciseTitle} progress tracking for ${muscleTitle} workouts`} 
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Header 
        title="Gym Progress Analytics"
        subtitle={`${muscleTitle} - ${exerciseTitle}`}
      />

      <main className="container mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">
              Welcome back, {user?.firstName || user?.name || 'User'}!
            </h2>
            <p className="text-xl text-gray-600">
              Your {exerciseTitle} Progress Journey
            </p>
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">
                <strong>Exercise:</strong> {exerciseTitle} | 
                <strong> Muscle Group:</strong> {muscleTitle} | 
                <strong> Data Source:</strong> Telegram Gym Bot
              </p>
            </div>
          </div>
          
          {/* Pass initial muscle and exercise to the chart component */}
          <div className="w-full">
            <ExerciseProgressChart 
              initialMuscle={muscleTitle}
              initialExercise={exerciseTitle}
            />
          </div>
          
        </div>
      </main>
    </div>
  );
};

export default ExercisePage;