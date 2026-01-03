import psycopg2
from psycopg2 import pool, sql
from contextlib import contextmanager
from datetime import datetime
from .logging import Logger

logger = Logger(name="postgres")

class PostgresDB:
    _pool = None

    def __init__(self, db_name, user, password, host, port):
        if PostgresDB._pool is None:
            PostgresDB._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dbname=db_name,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=30,
            )
            logger.info("Database connection pool created (min=2, max=10)")

    @contextmanager
    def get_connection(self):
        """Context manager for acquiring and releasing connections."""
        conn = None
        try:
            conn = PostgresDB._pool.getconn()
            yield conn
        finally:
            if conn:
                PostgresDB._pool.putconn(conn)

    @contextmanager
    def get_cursor(self):
        """Context manager for executing queries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()

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

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                logger.info(f"Successfully saved training data for user {user_id}")
                return {"success": True, "rows": cursor.rowcount}
        except Exception as e:
            logger.error(f"Database error saving training data: {e}")
            return {"success": False, "error": str(e)}

    def update_training_data(self, training_id, user_id, weight, reps):
        """
        Update an existing training record.
        Only allows updating weight and reps for now, as changing exercise/muscle/set
        might require more complex validation or is better handled by deleting and re-creating.
        """
        logger.info(f"Updating training data: id={training_id}, user_id={user_id}")

        query = '''
            UPDATE training
            SET weight = %s, reps = %s
            WHERE id = %s AND user_id = %s
        '''
        params = (weight, reps, training_id, user_id)

        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                if cursor.rowcount > 0:
                    logger.info(f"Successfully updated training {training_id}")
                    return {"success": True}
                else:
                    logger.warning(f"Training {training_id} not found or not owned by user {user_id}")
                    return {"success": False, "error": "Training not found or access denied"}
        except Exception as e:
            logger.error(f"Database error updating training data: {e}")
            return {"success": False, "error": str(e)}

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
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id, body_part, exercise_name))
            result = cursor.fetchone()
            return result

    def get_user(self, user_id):
        query = '''
            SELECT id
            FROM users
            WHERE id = %s
        '''
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result

    def save_any_data(self, table_name, data):
        columns = data.keys()
        values = data.values()
        query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() * len(values))
        )
        with self.get_cursor() as cursor:
            cursor.execute(query, list(values))

    def close(self):
        if PostgresDB._pool:
            PostgresDB._pool.closeall()
            logger.info("Database connection pool closed")

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
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id, muscle_name, exercise_name, date))
            results = cursor.fetchall()
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
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id, muscle_name, exercise_name))
            results = cursor.fetchall()
            logger.info(f"Training history for user {user_id}, exercise {exercise_name}: {len(results)} records found (excluding today)")
            return results

    def get_personal_record(self, user_id, muscle_name, exercise_name):
        """
        Get the personal record (maximum weight) for a specific user, muscle, and exercise.
        Returns the maximum weight and the date it was first achieved.
        """
        query = '''
            SELECT t.weight, t.reps, t.date
            FROM training t
            JOIN muscles m ON t.muscle_id = m.id
            JOIN exercises e ON t.exercise_id = e.id
            WHERE t.user_id = %s
            AND m.name = %s
            AND e.name = %s
            ORDER BY t.weight DESC, t.reps DESC, t.date DESC
            LIMIT 1
        '''
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id, muscle_name, exercise_name))
            result = cursor.fetchone()
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
        with self.get_cursor() as cursor:
            cursor.execute(query, (user_id, muscle_name, limit))
            results = cursor.fetchall()
            logger.info(f"Top exercises for user {user_id}, muscle {muscle_name}: {len(results)} exercises found")
            return results

    def get_all_muscles(self, user_id=None):
        """
        Get all muscle groups visible to the user.
        - Global muscles NOT hidden by user
        - Private muscles created by user
        """
        with self.get_cursor() as cursor:
            if user_id:
                query = '''
                    SELECT name FROM muscles
                    WHERE (is_global = TRUE AND id NOT IN (SELECT muscle_id FROM user_hidden_muscles WHERE user_id = %s))
                    OR (created_by = %s)
                    ORDER BY name ASC
                '''
                cursor.execute(query, (user_id, user_id))
            else:
                query = 'SELECT name FROM muscles WHERE is_global = TRUE ORDER BY name ASC'
                cursor.execute(query)

            results = cursor.fetchall()
            logger.info(f"Retrieved {len(results)} muscle groups for user {user_id}")
            return [row[0] for row in results]

    def get_exercises_by_muscle(self, muscle_name, user_id=None):
        """
        Get exercises for a muscle visible to the user.
        """
        with self.get_cursor() as cursor:
            if user_id:
                query = '''
                    SELECT e.name
                    FROM exercises e
                    JOIN muscles m ON e.muscle = m.id
                    WHERE m.name = %s
                    AND (
                        (e.is_global = TRUE AND e.id NOT IN (SELECT exercise_id FROM user_hidden_exercises WHERE user_id = %s))
                        OR (e.created_by = %s)
                    )
                    ORDER BY e.name ASC
                '''
                cursor.execute(query, (muscle_name, user_id, user_id))
            else:
                query = '''
                    SELECT e.name
                    FROM exercises e
                    JOIN muscles m ON e.muscle = m.id
                    WHERE m.name = %s AND e.is_global = TRUE
                    ORDER BY e.name ASC
                '''
                cursor.execute(query, (muscle_name,))

            results = cursor.fetchall()
            logger.info(f"Retrieved {len(results)} exercises for muscle {muscle_name} (user {user_id})")
            return [row[0] for row in results]

    def add_muscle(self, muscle_name, user_id=None):
        """
        Add a muscle.
        If it exists (Global or Private for user), return its ID.
        If not, create it (Private if user_id provided, else Global).
        """
        try:
            with self.get_cursor() as cursor:
                # Check if exists (Global OR Private for user)
                cursor.execute('''
                    SELECT id FROM muscles
                    WHERE name = %s
                    AND (is_global = TRUE OR created_by = %s)
                    ORDER BY is_global DESC LIMIT 1
                ''', (muscle_name, user_id))

                muscle_id = cursor.fetchone()

                if not muscle_id:
                    is_global = user_id is None
                    created_by = user_id

                    query = '''
                        INSERT INTO muscles (name, is_global, created_by)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    '''
                    cursor.execute(query, (muscle_name, is_global, created_by))
                    muscle_id = cursor.fetchone()

                return muscle_id[0] if muscle_id else None
        except Exception as e:
            logger.error(f"Error adding muscle: {e}")
            return None

    def add_exercise(self, exercise_name, muscle_name, user_id=None):
        """
        Add an exercise. If user_id is provided, it's a private exercise.
        """
        try:
            with self.get_cursor() as cursor:
                # Let's try to find the muscle ID first.
                cursor.execute('''
                    SELECT id FROM muscles
                    WHERE name = %s
                    AND (is_global = TRUE OR created_by = %s)
                    ORDER BY is_global DESC LIMIT 1
                ''', (muscle_name, user_id))
                existing_muscle = cursor.fetchone()

                if existing_muscle:
                    muscle_id = existing_muscle[0]
                else:
                    # Create new muscle. If user_id is present, it will be private.
                    muscle_id = self.add_muscle(muscle_name, user_id)

                if not muscle_id:
                    return None

                is_global = user_id is None
                created_by = user_id

                # Check if exercise exists
                if is_global:
                    cursor.execute('SELECT id FROM exercises WHERE name = %s AND muscle = %s AND is_global = TRUE', (exercise_name, muscle_id))
                else:
                    cursor.execute('SELECT id FROM exercises WHERE name = %s AND muscle = %s AND created_by = %s', (exercise_name, muscle_id, user_id))

                exercise_id = cursor.fetchone()

                if not exercise_id:
                    query = '''
                        INSERT INTO exercises (name, muscle, is_global, created_by)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    '''
                    cursor.execute(query, (exercise_name, muscle_id, is_global, created_by))
                    exercise_id = cursor.fetchone()

                return exercise_id[0] if exercise_id else None
        except Exception as e:
            logger.error(f"Error adding exercise: {e}")
            return None

    def hide_exercise(self, user_id, exercise_name, muscle_name):
        """
        Hide a global exercise for a user.
        """
        try:
            with self.get_cursor() as cursor:
                # Find the exercise ID (must be global)
                query = '''
                    SELECT e.id FROM exercises e
                    JOIN muscles m ON e.muscle = m.id
                    WHERE e.name = %s AND m.name = %s AND e.is_global = TRUE
                '''
                cursor.execute(query, (exercise_name, muscle_name))
                result = cursor.fetchone()

                if result:
                    exercise_id = result[0]
                    cursor.execute(
                        "INSERT INTO user_hidden_exercises (user_id, exercise_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (user_id, exercise_id)
                    )
                    return True
                return False
        except Exception as e:
            logger.error(f"Error hiding exercise: {e}")
            return False

    def delete_private_exercise(self, user_id, exercise_name, muscle_name):
        """
        Delete a private exercise.
        """
        try:
            with self.get_cursor() as cursor:
                query = '''
                    DELETE FROM exercises e
                    USING muscles m
                    WHERE e.muscle = m.id
                    AND e.name = %s AND m.name = %s
                    AND e.created_by = %s
                '''
                cursor.execute(query, (exercise_name, muscle_name, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting private exercise: {e}")
            return False