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
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    muscle INT REFERENCES muscles(id),
    CONSTRAINT unique_exercise UNIQUE (name, muscle)
);

CREATE TABLE IF NOT EXISTS training (
    id CHAR(32) PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    user_id BIGINT REFERENCES users(id),
    muscle_id INT REFERENCES muscles(id),
    exercise_id INT REFERENCES exercises(id),
    set INT,
    weight DECIMAL(5, 2),
    reps INT
);