import { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from 'next-auth';
import { authConfig } from '../../lib/auth';
import { getExerciseDataForUser } from '../../lib/database';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get user session
    const session = await getServerSession(req, res, authConfig);
    
    if (!session?.user) {
      return res.status(401).json({ error: 'Unauthorized - Please login' });
    }

    // Get username from session
    const user = session.user as any;
    const username = user.telegramUsername;
    
    if (!username) {
      return res.status(400).json({ error: 'No Telegram username found in session' });
    }

    // Get muscle and exercise from query parameters
    const muscle = req.query.muscle as string || 'Chest';
    const exercise = req.query.exercise as string || 'Bench press';
    
    // Fetch data for the authenticated user
    const data = await getExerciseDataForUser(username, muscle, exercise);
    
    // Transform data for ECharts
    const chartData = transformDataForChart(data);
    
    res.status(200).json(chartData);
  } catch (error) {
    console.error('Error fetching bench press data:', error);
    res.status(500).json({ error: 'Failed to fetch data' });
  }
}

function transformDataForChart(data: any[]) {
  // Group data by date and find max weight per day
  const groupedByDate: { [key: string]: any[] } = {};
  
  data.forEach(item => {
    if (!groupedByDate[item.date]) {
      groupedByDate[item.date] = [];
    }
    groupedByDate[item.date].push(item);
  });

  // Get all unique dates sorted
  const dates = Object.keys(groupedByDate).sort();

  // Create single series with max weight per day
  const maxWeightData = dates.map(date => {
    const dayData = groupedByDate[date];
    const maxWeight = Math.max(...dayData.map(item => item.weight));
    return maxWeight;
  });

  const series = [{
    name: 'Max Weight',
    type: 'line',
    smooth: true,
    data: maxWeightData,
    connectNulls: false,
    lineStyle: {
      width: 3
    },
    showSymbol: true,
    symbol: 'circle',
    symbolSize: 8,
    markPoint: {
      data: [
        { type: 'max', name: 'Max' },
        { type: 'min', name: 'Min' }
      ]
    },
    markLine: {
      data: [{ type: 'average', name: 'Average' }]
    }
  }];

  return {
    dates,
    series
  };
}
