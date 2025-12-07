CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    registration_date TIMESTAMP NOT NULL,
    last_interaction TIMESTAMP,
    lastname VARCHAR(255),
    first_name VARCHAR(255),
    phone VARCHAR(20),
    country VARCHAR(255),
    username VARCHAR(255),
    bio TEXT
);

CREATE TABLE IF NOT EXISTS muscles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_global BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id)
);
-- Unique index for global muscles
CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_global ON muscles (name) WHERE created_by IS NULL;
-- Unique index for user-specific muscles
CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_user ON muscles (name, created_by) WHERE created_by IS NOT NULL;

CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    muscle INT REFERENCES muscles(id),
    is_global BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id)
);
-- Unique index for global exercises
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_global ON exercises (name, muscle) WHERE created_by IS NULL;
-- Unique index for user-specific exercises
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_user ON exercises (name, muscle, created_by) WHERE created_by IS NOT NULL;

CREATE TABLE IF NOT EXISTS user_hidden_exercises (
    user_id BIGINT REFERENCES users(id),
    exercise_id INT REFERENCES exercises(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, exercise_id)
);

CREATE TABLE IF NOT EXISTS user_hidden_muscles (
    user_id BIGINT REFERENCES users(id),
    muscle_id INT REFERENCES muscles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, muscle_id)
);

CREATE TABLE IF NOT EXISTS training (
    id VARCHAR(32) PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    user_id BIGINT REFERENCES users(id),
    muscle_id INT REFERENCES muscles(id),
    exercise_id INT REFERENCES exercises(id),
    set INT,
    weight DECIMAL(5, 2),
    reps DECIMAL(5, 2)
);