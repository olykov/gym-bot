-- Migration 001 — hot-path indexes (GYM-4)
-- Idempotent: safe to run any number of times against the live DB.
-- init.sql only runs on a fresh volume, so the EXISTING production DB needs this applied once.
--
-- Apply on the server:
--   docker exec -i gymbot_db psql -U "$DB_USER" -d "$DB_NAME" < 001_add_hot_indexes.sql
--
-- training is small, so a brief lock is fine; IF NOT EXISTS makes re-runs no-ops.

CREATE INDEX IF NOT EXISTS idx_training_user_date ON training (user_id, date);
CREATE INDEX IF NOT EXISTS idx_training_exercise_id ON training (exercise_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
