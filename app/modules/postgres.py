import psycopg2
from psycopg2 import sql
from datetime import datetime
from .logging import Logger

logger = Logger(name="postgres")

class PostgresDB:
    def __init__(self, db_name, user, password, host='db', port='5432'):
        self.conn = psycopg2.connect(dbname=db_name, user=user, password=password, host=host, port=port)
        self.cursor = self.conn.cursor()

    def save_training_data(self, id, date, user_id, muscle_name, exercise_name, set_num, weight, reps):
        # Add logging to debug
        logger.info(f"Saving training data: user_id={user_id}, muscle={muscle_name}, exercise={exercise_name}")
        
        query = '''
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (%s, %s, %s, 
                (SELECT id FROM muscles WHERE name = %s LIMIT 1), 
                (SELECT id FROM exercises WHERE name = %s LIMIT 1), 
                %s, %s, %s)
        '''
        params = (id, date, user_id, muscle_name, exercise_name, set_num, weight, reps)
        logger.info(f"Query params: {params}")
        
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor.rowcount

    def get_latest_training(self, user_id, body_part, exercise_name):
        query = '''
            SELECT t.date, t.set, t.weight, t.reps 
            FROM training t
            JOIN users u ON t.user_id = u.id
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE u.id = %s AND m.body_part = %s AND e.name = %s
            ORDER BY t.date DESC LIMIT 1
        '''
        self.cursor.execute(query, (user_id, body_part, exercise_name))
        result = self.cursor.fetchone()
        return result

    def get_user(self, user_id):
        query = '''
            SELECT id
            FROM users
            WHERE id = %s
        '''
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()
        return result
    
    def add_muscle(self, muscle_name):
        try:
            self.cursor.execute('SELECT id FROM muscles WHERE name = %s', (muscle_name,))
            muscle_id = self.cursor.fetchone()
        except:
            muscle_id = None

        if not muscle_id:
            query = '''
                INSERT INTO muscles (name) 
                VALUES (%s) 
                RETURNING id
            '''
            try:
                self.cursor.execute(query, (muscle_name,))
                muscle_id = self.cursor.fetchone()
                self.conn.commit()
            except:
                muscle_id = None

        return muscle_id[0] if muscle_id else None

    # def add_muscle(self, muscle_name):
    #     query = '''
    #         INSERT INTO muscles (name) 
    #         VALUES (%s) 
    #         ON CONFLICT (name) DO NOTHING 
    #         RETURNING id
    #     '''
    #     self.cursor.execute(query, (muscle_name,))
    #     muscle_id = self.cursor.fetchone()

    #     if not muscle_id:
    #         self.cursor.execute('SELECT id FROM muscles WHERE name = %s', (muscle_name,))
    #         muscle_id = self.cursor.fetchone()

    #     self.conn.commit()
    #     return muscle_id[0] if muscle_id else None
    
    def add_exercise(self, exercise_name, muscle_name):
        muscle_id = self.add_muscle(muscle_name)
        if not muscle_id:
            return None

        self.cursor.execute('SELECT id FROM exercises WHERE name = %s AND muscle = %s', (exercise_name, muscle_id))
        exercise_id = self.cursor.fetchone()

        if not exercise_id:
            query = '''
                INSERT INTO exercises (name, muscle) 
                VALUES (%s, %s) 
                RETURNING id
            '''
            self.cursor.execute(query, (exercise_name, muscle_id))
            exercise_id = self.cursor.fetchone()
            self.conn.commit()

        return exercise_id[0] if exercise_id else None

    # def add_exercise(self, exercise_name, muscle_name):
    #     muscle_id = self.add_muscle(muscle_name)
    #     if not muscle_id:
    #         return None

    #     query = '''
    #         INSERT INTO exercises (name, muscle) 
    #         VALUES (%s, %s) 
    #         ON CONFLICT ON CONSTRAINT unique_exercise DO NOTHING 
    #         RETURNING id
    #     '''
    #     self.cursor.execute(query, (exercise_name, muscle_id))
    #     exercise_id = self.cursor.fetchone()

    #     if not exercise_id:
    #         self.cursor.execute('SELECT id FROM exercises WHERE name = %s AND muscle = %s', (exercise_name, muscle_id))
    #         exercise_id = self.cursor.fetchone()

    #     self.conn.commit()
    #     return exercise_id[0] if exercise_id else None

    def save_any_data(self, table_name, data):
        columns = data.keys()
        values = data.values()
        query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(values))
        )
        self.cursor.execute(query, list(values))
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_completed_sets(self, user_id, muscle_name, exercise_name, date):
        query = '''
            SELECT DISTINCT t.set
            FROM training t
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.user_id = %s 
            AND m.name = %s 
            AND e.name = %s 
            AND DATE(t.date) = DATE(%s)
        '''
        self.cursor.execute(query, (user_id, muscle_name, exercise_name, date))
        results = self.cursor.fetchall()
        logger.info(f"result: {results}")
        return [row[0] for row in results]

    def get_last_training_history(self, user_id, muscle_name, exercise_name):
        """
        Get the last training history for a specific user, muscle, and exercise.
        Excludes today's training to show only previous complete sessions.
        Returns all training records for this exercise ordered by date (most recent first).
        """
        query = '''
            SELECT t.date, t.set, t.weight, t.reps 
            FROM training t
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.user_id = %s 
            AND m.name = %s 
            AND e.name = %s
            AND DATE(t.date) < DATE(CURRENT_DATE)
            ORDER BY t.date DESC, t.set ASC
        '''
        self.cursor.execute(query, (user_id, muscle_name, exercise_name))
        results = self.cursor.fetchall()
        logger.info(f"Training history for user {user_id}, exercise {exercise_name}: {len(results)} records found (excluding today)")
        return results

    def get_personal_record(self, user_id, muscle_name, exercise_name):
        """
        Get the personal record (maximum weight) for a specific user, muscle, and exercise.
        Returns the maximum weight and the date it was first achieved.
        """
        query = '''
            SELECT t.weight, t.date 
            FROM training t
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.user_id = %s 
            AND m.name = %s 
            AND e.name = %s
            ORDER BY t.weight DESC, t.date DESC
            LIMIT 1
        '''
        self.cursor.execute(query, (user_id, muscle_name, exercise_name))
        result = self.cursor.fetchone()
        logger.info(f"Personal record for user {user_id}, exercise {exercise_name}: {result}")
        return result

    def get_top_exercises_for_muscle(self, user_id, muscle_name, limit=5):
        """
        Get the most frequently used exercises for a specific muscle group by user.
        Returns exercise names ordered by total training sessions (descending), then alphabetically.
        
        Args:
            user_id: User's Telegram ID
            muscle_name: Name of the muscle group
            limit: Maximum number of exercises to return (default: 5)
            
        Returns:
            List of tuples: [(exercise_name, frequency), ...] or empty list
        """
        query = '''
            SELECT e.name, COUNT(*) as frequency
            FROM training t
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.user_id = %s AND m.name = %s
            GROUP BY e.name
            ORDER BY frequency DESC, e.name ASC
            LIMIT %s
        '''
        self.cursor.execute(query, (user_id, muscle_name, limit))
        results = self.cursor.fetchall()
        logger.info(f"Top exercises for user {user_id}, muscle {muscle_name}: {len(results)} exercises found")
        return results