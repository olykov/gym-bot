import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useSession } from 'next-auth/react';

interface ChartData {
  dates: string[];
  series: Array<{
    name: string;
    type: string;
    smooth: boolean;
    data: (number | null)[];
    connectNulls: boolean;
  }>;
}

interface MuscleGroup {
  name: string;
  exercises: string[];
  totalSessions: number;
}

interface UserExercises {
  muscles: MuscleGroup[];
  mostUsed: { muscle: string; exercise: string } | null;
}

type DatePeriod = 'This Week' | 'This Month' | 'This Quarter' | 'This Year' | 'All Time';

interface ExerciseProgressChartProps {
  initialMuscle?: string;
  initialExercise?: string;
}

const ExerciseProgressChart: React.FC<ExerciseProgressChartProps> = ({
  initialMuscle,
  initialExercise
}) => {
  const { data: session, status } = useSession();
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [filteredChartData, setFilteredChartData] = useState<ChartData | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<DatePeriod>('All Time');
  const [userExercises, setUserExercises] = useState<UserExercises | null>(null);
  const [selectedMuscle, setSelectedMuscle] = useState<string>('');
  const [selectedExercise, setSelectedExercise] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [exercisesLoading, setExercisesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'authenticated' && session) {
      fetchUserExercises();
    } else if (status === 'unauthenticated') {
      setError('Please login to view your data');
      setLoading(false);
      setExercisesLoading(false);
    }
  }, [session, status]);

  // Fetch chart data when muscle/exercise selection changes
  useEffect(() => {
    if (selectedMuscle && selectedExercise) {
      fetchExerciseData();
    }
  }, [selectedMuscle, selectedExercise]);

  useEffect(() => {
    if (chartData) {
      filterDataByPeriod();
    }
  }, [chartData, selectedPeriod]);

  const getDateRange = (period: DatePeriod): { start: Date; end: Date } => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    switch (period) {
      case 'This Week': {
        const startOfWeek = new Date(today);
        const day = startOfWeek.getDay();
        const diff = startOfWeek.getDate() - day + (day === 0 ? -6 : 1); // Monday
        startOfWeek.setDate(diff);
        return { start: startOfWeek, end: today };
      }
      case 'This Month': {
        const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        return { start: startOfMonth, end: today };
      }
      case 'This Quarter': {
        const quarter = Math.floor(today.getMonth() / 3);
        const startOfQuarter = new Date(today.getFullYear(), quarter * 3, 1);
        return { start: startOfQuarter, end: today };
      }
      case 'This Year': {
        const startOfYear = new Date(today.getFullYear(), 0, 1);
        return { start: startOfYear, end: today };
      }
      case 'All Time':
      default:
        return { start: new Date(0), end: new Date(8640000000000000) }; // Max date
    }
  };

  const filterDataByPeriod = () => {
    if (!chartData) return;

    if (selectedPeriod === 'All Time') {
      setFilteredChartData(chartData);
      return;
    }

    const { start, end } = getDateRange(selectedPeriod);
    const filteredDates: string[] = [];
    const filteredIndices: number[] = [];

    chartData.dates.forEach((date, index) => {
      const dateObj = new Date(date);
      if (dateObj >= start && dateObj <= end) {
        filteredDates.push(date);
        filteredIndices.push(index);
      }
    });

    const filteredSeries = chartData.series.map(series => ({
      ...series,
      data: filteredIndices.map(index => series.data[index])
    }));

    setFilteredChartData({
      dates: filteredDates,
      series: filteredSeries
    });
  };

  const fetchUserExercises = async () => {
    try {
      const response = await fetch('/api/user-exercises');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('🏋️ User exercises fetch failed:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const exercises: UserExercises = await response.json();
      setUserExercises(exercises);
      
      // Set default selections - prioritize initial props from URL
      if (initialMuscle && initialExercise) {
        // Validate that the initial muscle/exercise exists in user's data (case-insensitive)
        const muscleExists = exercises.muscles.find(m => 
          m.name.toLowerCase() === initialMuscle.toLowerCase()
        );
        const exerciseExists = muscleExists?.exercises.find(e => 
          e.toLowerCase() === initialExercise.toLowerCase()
        );
        
        if (muscleExists && exerciseExists) {
          console.log(`✅ URL Navigation: ${muscleExists.name} - ${exerciseExists}`);
          setSelectedMuscle(muscleExists.name);  // Use exact name from database
          setSelectedExercise(exerciseExists);   // Use exact name from database
        } else {
          // Fall back to default if URL params are invalid
          console.warn(`❌ Invalid URL: ${initialMuscle}/${initialExercise} not found`);
          setDefaultSelections(exercises);
        }
      } else {
        setDefaultSelections(exercises);
      }
      
      setExercisesLoading(false);
    } catch (err) {
      console.error('🏋️ Exercises load error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load exercises');
      setExercisesLoading(false);
    }
  };

  const setDefaultSelections = (exercises: UserExercises) => {
    if (exercises.mostUsed) {
      setSelectedMuscle(exercises.mostUsed.muscle);
      setSelectedExercise(exercises.mostUsed.exercise);
    } else if (exercises.muscles.length > 0) {
      const firstMuscle = exercises.muscles[0];
      setSelectedMuscle(firstMuscle.name);
      setSelectedExercise(firstMuscle.exercises[0] || '');
    }
  };

  const fetchExerciseData = async () => {
    try {
      const params = new URLSearchParams({
        muscle: selectedMuscle,
        exercise: selectedExercise
      });
      const response = await fetch(`/api/bench-press-data?${params}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('📊 Exercise data fetch failed:', errorText);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log(`📊 Loaded ${data.dates?.length || 0} training sessions for ${selectedExercise}`);
      setChartData(data);
    } catch (err) {
      console.error('📊 Exercise data error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleMuscleChange = (muscle: string) => {
    setSelectedMuscle(muscle);
    
    // Auto-select first exercise in the muscle group
    const muscleGroup = userExercises?.muscles.find(m => m.name === muscle);
    if (muscleGroup && muscleGroup.exercises.length > 0) {
      setSelectedExercise(muscleGroup.exercises[0]);
    }
  };

  const handleExerciseChange = (exercise: string) => {
    setSelectedExercise(exercise);
  };


  if (loading || exercisesLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="text-lg text-gray-600">
          {exercisesLoading ? 'Loading exercises...' : 'Loading exercise data...'}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="text-lg text-red-600">Error: {error}</div>
      </div>
    );
  }

  // If no exercises available at all, show empty state
  if (!userExercises || userExercises.muscles.length === 0) {
    const username = (session?.user as any)?.telegramUsername || 'Unknown';
    return (
      <div className="w-full">
        {/* Empty Exercise Filters */}
        <div className="mb-6 px-4">
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center max-w-4xl mx-auto">
            <div className="flex flex-col w-full sm:w-auto">
              <label className="text-sm font-medium text-gray-700 mb-1">Muscle Group:</label>
              <select disabled className="px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-400 min-w-[140px]">
                <option>No muscles available</option>
              </select>
            </div>
            <div className="flex flex-col w-full sm:w-auto">
              <label className="text-sm font-medium text-gray-700 mb-1">Exercise:</label>
              <select disabled className="px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-400 min-w-[160px]">
                <option>No exercises available</option>
              </select>
            </div>
          </div>
        </div>
        
        <div className="flex justify-center items-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <div className="text-center">
            <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <div className="text-lg text-gray-600 mb-2">No exercise data found for user "{username}"</div>
            <div className="text-sm text-gray-500">Start logging workouts to see your progress here</div>
          </div>
        </div>
      </div>
    );
  }

  const option = {
    color: ['#37A2FF'],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function (params: any) {
        const param = params[0];
        const date = new Date(param.axisValue);
        const formattedDate = `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()}`;
        return `<div><strong>${formattedDate}</strong></div><div style="color: ${param.color};">● Max Weight: ${param.value}kg</div>`;
      }
    },
    legend: {
      show: false
    },
    toolbox: {
      show: false
    },
    grid: {
      top: 40,
      left: 60,
      right: 60,
      bottom: 60
    },
    xAxis: [
      {
        type: 'category',
        boundaryGap: false,
        data: filteredChartData?.dates || [],
        axisLabel: {
          rotate: 45,
          formatter: function (value: string) {
            // Format date as DD/MM
            const date = new Date(value);
            return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}`;
          }
        }
      }
    ],
    yAxis: [
      {
        type: 'value',
        name: 'Weight (kg)',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          fontSize: 14,
          fontWeight: 'bold'
        },
        axisLabel: {
          formatter: '{value} kg'
        },
        scale: true,
        min: function(value: any) {
          // Start from 90% of minimum value, rounded down to nearest 5
          const minValue = Math.floor(value.min * 0.9);
          return Math.floor(minValue / 5) * 5;
        },
        max: function(value: any) {
          // End at 110% of maximum value, rounded up to nearest 5
          const maxValue = Math.ceil(value.max * 1.1);
          return Math.ceil(maxValue / 5) * 5;
        }
      }
    ],
    series: filteredChartData?.series || []
  };

  const periods: DatePeriod[] = ['This Week', 'This Month', 'This Quarter', 'This Year', 'All Time'];
  const hasFilteredData = filteredChartData && filteredChartData.series.length > 0 && filteredChartData.dates.length > 0;
  
  // Get available exercises for selected muscle
  const availableExercises = userExercises?.muscles.find(m => m.name === selectedMuscle)?.exercises || [];

  return (
    <div className="w-full">
      {/* Exercise Filter Dropdowns */}
      <div className="mb-6 px-4">
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center max-w-4xl mx-auto">
          {/* Muscle Group Dropdown */}
          <div className="flex flex-col w-full sm:w-auto">
            <label className="text-sm font-medium text-gray-700 mb-1">Muscle Group:</label>
            <select
              value={selectedMuscle}
              onChange={(e) => handleMuscleChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[140px]"
            >
              {userExercises?.muscles.map((muscle) => (
                <option key={muscle.name} value={muscle.name}>
                  {muscle.name} ({muscle.exercises.length})
                </option>
              ))}
            </select>
          </div>

          {/* Exercise Dropdown */}
          <div className="flex flex-col w-full sm:w-auto">
            <label className="text-sm font-medium text-gray-700 mb-1">Exercise:</label>
            <select
              value={selectedExercise}
              onChange={(e) => handleExerciseChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[160px]"
            >
              {availableExercises.map((exercise) => (
                <option key={exercise} value={exercise}>
                  {exercise}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Custom Chart Title */}
      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold text-gray-800">
          {selectedExercise} Progress
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Max weight lifted per training session
        </p>
      </div>

      {/* Date Range Filter Buttons */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2 justify-center">
          {periods.map((period) => (
            <button
              key={period}
              onClick={() => setSelectedPeriod(period)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                selectedPeriod === period
                  ? 'bg-blue-600 text-white shadow-lg scale-105'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:text-gray-900'
              }`}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Chart or No Data Message */}
      {hasFilteredData ? (
        <ReactECharts 
          option={option} 
          style={{ height: '600px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      ) : (
        <div className="flex justify-center items-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <div className="text-center">
            <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <div className="text-lg text-gray-600 mb-2">No data available for {selectedExercise} - {selectedPeriod.toLowerCase()}</div>
            <div className="text-sm text-gray-500">Try selecting a different time period or exercise above</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExerciseProgressChart;
