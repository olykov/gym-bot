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

-- Canonical name-normalization function (GYM-84). SINGLE SOURCE OF TRUTH for
-- the lexical dedup key: lower -> unify '-'/'_' to space -> strip incidental
-- punctuation ('.,) -> collapse whitespace -> trim. IMMUTABLE so it can back
-- the generated name_key columns + their unique indexes, and so the Core API
-- (GYM-85) can call the SAME function for write-path lookups. Mirrors
-- packages/db/alembic/versions/0004_name_key.py.
CREATE OR REPLACE FUNCTION public.app_name_key(p_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $fn$
    SELECT btrim(
        regexp_replace(
            translate(
                translate(lower(p_name), '-_', '  '),
                E'\'`.,', ''
            ),
            '\s+', ' ', 'g'
        )
    )
$fn$;

CREATE TABLE IF NOT EXISTS muscles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_key TEXT GENERATED ALWAYS AS (public.app_name_key(name)) STORED,
    is_global BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id)
);
-- Unique index for global muscles (dedup on normalized name_key; GYM-84)
CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_key_global ON muscles (name_key) WHERE created_by IS NULL;
-- Unique index for user-specific muscles (dedup on normalized name_key; GYM-84)
CREATE UNIQUE INDEX IF NOT EXISTS idx_muscles_name_key_user ON muscles (name_key, created_by) WHERE created_by IS NOT NULL;

CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_key TEXT GENERATED ALWAYS AS (public.app_name_key(name)) STORED,
    muscle INT REFERENCES muscles(id),
    is_global BOOLEAN DEFAULT TRUE,
    created_by BIGINT REFERENCES users(id)
);
-- Unique index for global exercises (dedup on normalized name_key; GYM-84)
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_name_key_global ON exercises (name_key, muscle) WHERE created_by IS NULL;
-- Unique index for user-specific exercises (dedup on normalized name_key; GYM-84)
CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_name_key_user ON exercises (name_key, muscle, created_by) WHERE created_by IS NOT NULL;

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

-- Hot-path indexes (GYM-4): every analytics query filters user_id and joins/sorts on
-- date/exercise; without these the training table is sequentially scanned each request.
CREATE INDEX IF NOT EXISTS idx_training_user_date ON training (user_id, date);
CREATE INDEX IF NOT EXISTS idx_training_exercise_id ON training (exercise_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);