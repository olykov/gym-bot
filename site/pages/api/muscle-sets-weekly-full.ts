import { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from 'next-auth';
import { authConfig } from '../../lib/auth';
import pool from '../../lib/database';

interface WeeklyMuscleData {
  week: string;
  muscle: string;
  sets_count: number;
}

interface MuscleSetsSeries {
  name: string;
  data: number[];
}

interface MuscleSetsWeeklyResponse {
  weeks: string[];
  series: MuscleSetsSeries[];
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<MuscleSetsWeeklyResponse | { error: string }>) {
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
    
    // Fetch weekly muscle sets data for full 12 months
    const weeklyData = await getWeeklyMuscleSets(username);
    
    res.status(200).json(weeklyData);
  } catch (error) {
    console.error('Error fetching full weekly muscle sets:', error);
    res.status(500).json({ error: 'Failed to fetch weekly muscle sets data' });
  }
}

async function getWeeklyMuscleSets(username: string): Promise<MuscleSetsWeeklyResponse> {
  const client = await pool.connect();
  
  try {
    // Get weekly sets data by muscle for last 12 months (full version)
    const weeklyQuery = `
      WITH weekly_data AS (
        SELECT 
          TO_CHAR(DATE_TRUNC('week', t.date::date), 'YYYY-"W"WW') as week,
          COALESCE(
            CASE e.muscle
              WHEN 1 THEN 'Chest'
              WHEN 2 THEN 'Back' 
              WHEN 3 THEN 'Shoulders'
              WHEN 4 THEN 'Biceps'
              WHEN 5 THEN 'Triceps'
              WHEN 6 THEN 'Legs'
              WHEN 7 THEN 'Abs'
              WHEN 8 THEN 'Forearms'
              ELSE 'Muscle ' || e.muscle::text
            END,
            'Other'
          ) as muscle,
          COUNT(t.set) as sets_count
        FROM training t
        JOIN users u ON t.user_id = u.id
        JOIN exercises e ON t.exercise_id = e.id
        WHERE u.username = $1
          AND t.date >= CURRENT_DATE - INTERVAL '12 months'
          AND t.date <= CURRENT_DATE
        GROUP BY DATE_TRUNC('week', t.date::date), e.muscle
        ORDER BY DATE_TRUNC('week', t.date::date) ASC
      )
      SELECT week, muscle, sets_count
      FROM weekly_data
      ORDER BY week ASC, muscle ASC
    `;
    
    const result = await client.query(weeklyQuery, [username]);
    
    if (result.rows.length === 0) {
      return {
        weeks: [],
        series: []
      };
    }

    // Process the data to create the structure needed for ECharts
    const weeklyDataMap = new Map<string, Map<string, number>>();
    const musclesSet = new Set<string>();
    const weeksSet = new Set<string>();

    console.log('🔍 Full year raw data from query:', result.rows.slice(0, 3));

    // Build data structure
    result.rows.forEach((row: WeeklyMuscleData) => {
      const { week, muscle, sets_count } = row;
      
      weeksSet.add(week);
      musclesSet.add(muscle);
      
      if (!weeklyDataMap.has(week)) {
        weeklyDataMap.set(week, new Map());
      }
      
      weeklyDataMap.get(week)!.set(muscle, sets_count);
    });

    // Convert to arrays for ECharts
    const weeks = Array.from(weeksSet).sort();
    const muscles = Array.from(musclesSet).sort();
    
    console.log('📊 Full year processed data:', { 
      weeks: weeks.slice(0, 3), 
      muscles,
      totalWeeks: weeks.length 
    });
    
    // Build series data
    const series: MuscleSetsSeries[] = muscles.map(muscle => ({
      name: muscle,
      data: weeks.map(week => {
        const weekData = weeklyDataMap.get(week);
        return weekData?.get(muscle) || 0;
      })
    }));

    console.log('📈 Full year series data:', series.map(s => ({ name: s.name, dataPoints: s.data.length })));

    return {
      weeks,
      series
    };
    
  } catch (error) {
    console.error('❌ FullYearWeeklyMuscleSets: Database error:', error);
    throw error;
  } finally {
    client.release();
  }
}