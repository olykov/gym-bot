import psycopg2
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection parameters (matching docker-compose.local.yaml)
DB_NAME = os.environ.get("DB_NAME", "gymbot")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5400") # External port mapped in docker-compose.local.yaml

def run_migration():
    try:
        logger.info(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT}...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info("Connected successfully.")

        # 1. Add columns to muscles table
        logger.info("Altering muscles table...")
        try:
            cursor.execute("ALTER TABLE muscles ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;")
            cursor.execute("ALTER TABLE muscles ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);")
            
            # Drop old unique constraint if it exists (assuming standard name)
            # We need to handle the constraint carefully. 
            # First, let's check if the constraint exists and drop it.
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'muscles_name_key') THEN 
                        ALTER TABLE muscles DROP CONSTRAINT muscles_name_key; 
                    END IF; 
                END $$;
            """)
            
            # Add new unique indexes
            # 1. Unique name for global items (where created_by is NULL)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_global ON muscles (name) WHERE created_by IS NULL;")
            # 2. Unique name per user (where created_by is NOT NULL)
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_user ON muscles (name, created_by) WHERE created_by IS NOT NULL;")
            
        except Exception as e:
            logger.error(f"Error altering muscles table: {e}")

        # 2. Add columns to exercises table
        logger.info("Altering exercises table...")
        try:
            cursor.execute("ALTER TABLE exercises ADD COLUMN IF NOT EXISTS is_global BOOLEAN DEFAULT TRUE;")
            cursor.execute("ALTER TABLE exercises ADD COLUMN IF NOT EXISTS created_by BIGINT REFERENCES users(id);")
            
            # Drop old unique constraint
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_exercise') THEN 
                        ALTER TABLE exercises DROP CONSTRAINT unique_exercise; 
                    END IF; 
                END $$;
            """)
            
            # Add new unique indexes
            # 1. Unique name+muscle for global items
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_global ON exercises (name, muscle) WHERE created_by IS NULL;")
            # 2. Unique name+muscle per user
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_user ON exercises (name, muscle, created_by) WHERE created_by IS NOT NULL;")
            
        except Exception as e:
            logger.error(f"Error altering exercises table: {e}")

        # 3. Create user_hidden_exercises table
        logger.info("Creating user_hidden_exercises table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_hidden_exercises (
                user_id BIGINT REFERENCES users(id),
                exercise_id INT REFERENCES exercises(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, exercise_id)
            );
        """)

        # 4. Create user_hidden_muscles table
        logger.info("Creating user_hidden_muscles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_hidden_muscles (
                user_id BIGINT REFERENCES users(id),
                muscle_id INT REFERENCES muscles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, muscle_id)
            );
        """)

        logger.info("Migration completed successfully.")
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
