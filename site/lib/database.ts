import { Pool } from 'pg';

// Database connection configuration
const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT!),
});

export interface BenchPressData {
  date: string;
  set: number;
  weight: number;
  reps: number;
}

export async function getExerciseDataForUser(username: string, muscle: string, exercise: string): Promise<BenchPressData[]> {
  const client = await pool.connect();
  
  try {
    const query = `
      SELECT t.date, t.set, t.weight, t.reps 
      FROM training t
      JOIN users u ON t.user_id = u.id
      JOIN muscles m ON t.muscle_id = m.id
      JOIN exercises e ON t.exercise_id = e.id
      WHERE u.username = $1 
      AND m.name = $2 
      AND e.name = $3
      ORDER BY t.date ASC, t.set ASC
    `;
    
    const result = await client.query(query, [username, muscle, exercise]);
    
    if (result.rows.length === 0) {
      console.log('⚠️ Database: No data found - checking if user exists...');
      
      // Check if user exists at all
      const userCheck = await client.query('SELECT id, username FROM users WHERE username = $1', [username]);
      console.log(`🔍 Database: User check found ${userCheck.rows.length} users:`, userCheck.rows);
      
      // Check available exercises for this user
      const exerciseCheck = await client.query(`
        SELECT DISTINCT e.name as exercise, m.name as muscle 
        FROM training t
        JOIN users u ON t.user_id = u.id
        JOIN muscles m ON t.muscle_id = m.id
        JOIN exercises e ON t.exercise_id = e.id
        WHERE u.username = $1
      `, [username]);
      console.log(`🔍 Database: Available exercises for ${username}:`, exerciseCheck.rows);
    }
    
    const mappedData = result.rows.map(row => ({
      date: row.date.toISOString().split('T')[0], // Format as YYYY-MM-DD
      set: parseInt(row.set),
      weight: parseFloat(row.weight),
      reps: parseInt(row.reps)
    }));
    
    return mappedData;
  } catch (error) {
    console.error('❌ Database: Query error:', error);
    throw error;
  } finally {
    client.release();
  }
}

// Backward compatibility
export async function getBenchPressDataForUser(username: string): Promise<BenchPressData[]> {
  return getExerciseDataForUser(username, 'Chest', 'Bench press');
}

export default pool;
