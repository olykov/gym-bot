import { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from 'next-auth';
import { authConfig } from '../../lib/auth';
import pool from '../../lib/database';

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

interface UserActivityResponse {
  activityData: DailyActivity[];
  stats: UserStats;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<UserActivityResponse | { error: string }>) {
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
    
    // Fetch user's activity data
    const activityData = await getUserActivity(username);
    
    res.status(200).json(activityData);
  } catch (error) {
    console.error('Error fetching user activity:', error);
    res.status(500).json({ error: 'Failed to fetch activity data' });
  }
}

async function getUserActivity(username: string): Promise<UserActivityResponse> {
  const client = await pool.connect();
  
  try {
    // Get daily activity - SIMPLE STRING EXTRACTION (no timezone bullshit!)
    const activityQuery = `
      SELECT 
        SUBSTRING(t.date::text FROM 1 FOR 10) as date,
        COUNT(t.set) as sets_count
      FROM training t
      JOIN users u ON t.user_id = u.id
      WHERE u.username = $1
        AND SUBSTRING(t.date::text FROM 1 FOR 10) >= (CURRENT_DATE - INTERVAL '364 days')::text
        AND SUBSTRING(t.date::text FROM 1 FOR 10) <= (CURRENT_DATE + INTERVAL '7 days')::text
      GROUP BY SUBSTRING(t.date::text FROM 1 FOR 10)
      ORDER BY SUBSTRING(t.date::text FROM 1 FOR 10) ASC
    `;
    
    const activityResult = await client.query(activityQuery, [username]);
    
    // Get all-time stats
    const statsQuery = `
      SELECT 
        COUNT(DISTINCT DATE(t.date)) as total_trainings,
        COALESCE(SUM(t.weight * t.reps), 0) as total_weight_lifted,
        MIN(t.date) as first_training_date
      FROM training t
      JOIN users u ON t.user_id = u.id
      WHERE u.username = $1
    `;
    
    const statsResult = await client.query(statsQuery, [username]);
    
    // Get trainings this week (Monday to Sunday)
    const thisWeekQuery = `
      SELECT COUNT(DISTINCT DATE(t.date)) as trainings_this_week
      FROM training t
      JOIN users u ON t.user_id = u.id
      WHERE u.username = $1
        AND t.date >= DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 day'
        AND t.date < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '8 days'
    `;
    
    const thisWeekResult = await client.query(thisWeekQuery, [username]);
    
    // Get active days in last year for streak calculation (including future dates if any)
    const streakQuery = `
      SELECT DISTINCT t.date::date as date
      FROM training t
      JOIN users u ON t.user_id = u.id
      WHERE u.username = $1
        AND t.date >= CURRENT_DATE - INTERVAL '364 days'
      ORDER BY t.date::date ASC
      LIMIT 365
    `;
    
    const streakResult = await client.query(streakQuery, [username]);
    
    // Process activity data - fill missing days with 0
    const activityMap = new Map<string, number>();
    activityResult.rows.forEach(row => {
      const dateStr = row.date; // Already a string from SUBSTRING query
      activityMap.set(dateStr, parseInt(row.sets_count));
    });
    
    // Generate simple chronological 365-day array
    const activityData: DailyActivity[] = [];
    const today = new Date();
    
    // Start from 364 days ago to today (365 total days)
    for (let i = 364; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      activityData.push({
        date: dateStr,
        sets_count: activityMap.get(dateStr) || 0
      });
    }
    
    
    // Calculate streaks
    const activeDates = streakResult.rows.map(row => 
      row.date.toISOString().split('T')[0]
    );
    
    const { longestStreak } = calculateStreaks(activeDates);
    
    // Build stats
    const firstTrainingDate = statsResult.rows[0]?.first_training_date;
    const stats: UserStats = {
      totalTrainings: parseInt(statsResult.rows[0]?.total_trainings || '0'),
      totalWeightLifted: parseFloat(statsResult.rows[0]?.total_weight_lifted || '0'),
      activeDays: activeDates.length,
      trainingsThisWeek: parseInt(thisWeekResult.rows[0]?.trainings_this_week || '0'),
      longestStreak,
      firstTrainingDate: firstTrainingDate ? firstTrainingDate.toISOString().split('T')[0] : null
    };
    
    return {
      activityData,
      stats
    };
    
  } catch (error) {
    console.error('❌ UserActivity: Database error:', error);
    throw error;
  } finally {
    client.release();
  }
}

function calculateStreaks(activeDates: string[]): { longestStreak: number } {
  if (activeDates.length === 0) {
    return { longestStreak: 0 };
  }
  
  // Sort dates to ensure chronological order
  const sortedDates = [...activeDates].sort();
  
  let longestStreak = 0;
  let tempStreak = 1;
  
  // Calculate longest streak
  for (let i = 1; i < sortedDates.length; i++) {
    const prevDate = new Date(sortedDates[i - 1]);
    const currDate = new Date(sortedDates[i]);
    const dayDiff = Math.floor((currDate.getTime() - prevDate.getTime()) / (1000 * 60 * 60 * 24));
    
    if (dayDiff === 1) {
      tempStreak++;
    } else {
      longestStreak = Math.max(longestStreak, tempStreak);
      tempStreak = 1;
    }
  }
  longestStreak = Math.max(longestStreak, tempStreak);
  
  return { longestStreak };
}