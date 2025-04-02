import psycopg2
from psycopg2 import sql
from datetime import datetime
from .logging import Logger

logger = Logger(name="handlers")

class PostgresDB:
    def __init__(self, db_name, user, password, host='db', port='5432'):
        self.conn = psycopg2.connect(dbname=db_name, user=user, password=password, host=host, port=port)
        self.cursor = self.conn.cursor()

    def save_training_data(self, id, date, user_id, muscle_name, exercise_name, set_num, weight, reps):
        query = '''
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (%s, %s, %s, 
                (SELECT id FROM muscles WHERE name = %s LIMIT 1), 
                (SELECT id FROM exercises WHERE name = %s LIMIT 1), 
                %s, %s, %s)
        '''
        self.cursor.execute(query, (id, date, user_id, muscle_name, exercise_name, set_num, weight, reps))
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
        self.cursor.execute('SELECT id FROM muscles WHERE name = %s', (muscle_name,))
        muscle_id = self.cursor.fetchone()

        if not muscle_id:
            query = '''
                INSERT INTO muscles (name) 
                VALUES (%s) 
                RETURNING id
            '''
            self.cursor.execute(query, (muscle_name,))
            muscle_id = self.cursor.fetchone()
            self.conn.commit()

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
        logger.info(results)
        return [row[0] for row in results]