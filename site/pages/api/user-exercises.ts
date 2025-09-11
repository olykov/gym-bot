import { NextApiRequest, NextApiResponse } from 'next';
import { getServerSession } from 'next-auth';
import { authConfig } from '../../lib/auth';
import pool from '../../lib/database';

interface ExerciseData {
  muscle: string;
  exercise: string;
  session_count: number;
}

interface MuscleGroup {
  name: string;
  exercises: string[];
  totalSessions: number;
}

interface UserExercisesResponse {
  muscles: MuscleGroup[];
  mostUsed: { muscle: string; exercise: string } | null;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<UserExercisesResponse | { error: string }>) {
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
    
    // Fetch user's exercises grouped by muscle
    const exerciseData = await getUserExercises(username);
    
    res.status(200).json(exerciseData);
  } catch (error) {
    console.error('Error fetching user exercises:', error);
    res.status(500).json({ error: 'Failed to fetch exercises' });
  }
}

async function getUserExercises(username: string): Promise<UserExercisesResponse> {
  const client = await pool.connect();
  
  try {
    const query = `
      SELECT 
        m.name as muscle,
        e.name as exercise,
        COUNT(DISTINCT t.date) as session_count
      FROM training t
      JOIN users u ON t.user_id = u.id
      JOIN muscles m ON t.muscle_id = m.id
      JOIN exercises e ON t.exercise_id = e.id
      WHERE u.username = $1
      GROUP BY m.name, e.name
      ORDER BY session_count DESC, m.name ASC, e.name ASC
    `;
    
    const result = await client.query(query, [username]);
    
    if (result.rows.length === 0) {
      return {
        muscles: [],
        mostUsed: null
      };
    }

    // Group by muscle and calculate totals
    const muscleMap = new Map<string, { exercises: string[], totalSessions: number }>();
    let mostUsedExercise: ExerciseData | null = null;

    result.rows.forEach((row: ExerciseData) => {
      const muscle = row.muscle;
      const exercise = row.exercise;
      const sessionCount = typeof row.session_count === 'string' ? parseInt(row.session_count) : row.session_count;

      // Track most used exercise overall
      if (!mostUsedExercise || sessionCount > (typeof mostUsedExercise.session_count === 'string' ? parseInt(mostUsedExercise.session_count) : mostUsedExercise.session_count)) {
        mostUsedExercise = row;
      }

      // Group by muscle
      if (!muscleMap.has(muscle)) {
        muscleMap.set(muscle, { exercises: [], totalSessions: 0 });
      }
      
      const muscleData = muscleMap.get(muscle)!;
      muscleData.exercises.push(exercise);
      muscleData.totalSessions += sessionCount;
    });

    // Convert to response format
    const muscles: MuscleGroup[] = Array.from(muscleMap.entries()).map(([name, data]) => ({
      name,
      exercises: data.exercises,
      totalSessions: data.totalSessions
    }));


    return {
      muscles,
      mostUsed: mostUsedExercise ? { 
        muscle: (mostUsedExercise as ExerciseData).muscle, 
        exercise: (mostUsedExercise as ExerciseData).exercise 
      } : null
    };
  } catch (error) {
    console.error('❌ UserExercises: Database error:', error);
    throw error;
  } finally {
    client.release();
  }
}