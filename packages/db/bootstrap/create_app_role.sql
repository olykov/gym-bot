-- packages/db/bootstrap/create_app_role.sql
--
-- GYM-32 / GYM-34 — create the low-privilege role the Core API connects as.
--
-- This is NOT an Alembic migration: roles are cluster-global objects and the
-- password is a secret, so role creation lives in infra (GYM-34), not in the
-- versioned schema. The 0002_rls migration only ENABLEs/FORCEs RLS, creates
-- policies, and GRANTs to this role once it exists.
--
-- The role is NOSUPERUSER NOBYPASSRLS on purpose: RLS is ignored by superusers
-- and by BYPASSRLS roles, so the API MUST run as this unprivileged role for the
-- policies in 0002_rls to take effect. Tables remain owned by the migration/ops
-- role (`myuser`); app_rw only receives table/sequence GRANTs (from 0002_rls).
--
-- The password is supplied at run time via a psql variable named `app_pw`
-- (never hardcoded, never committed). Infra invokes it, e.g.:
--
--   psql "$ADMIN_DATABASE_URL" \
--        -v app_pw="$APP_DB_PASSWORD" \
--        -f packages/db/bootstrap/create_app_role.sql
--
-- ADMIN_DATABASE_URL connects as a superuser/role-admin (e.g. myuser);
-- APP_DB_PASSWORD comes from the deploy secret store. After this runs, set the
-- API's APP_DB_* / DATABASE_URL to connect as app_rw, then apply 0002_rls.
--
-- Idempotent: CREATE only when missing; ALTER ... PASSWORD on every run so a
-- re-invocation rotates the password to the current secret value.

\set ON_ERROR_STOP on

-- psql does NOT substitute :'app_pw' inside a dollar-quoted ($$...$$) block, so
-- we stash the secret into a session-local custom GUC at the top level (where
-- psql substitution into a quoted literal works), then read it inside the DO
-- block with current_setting() and pass it to a parameterized format(%L).
-- The GUC is session-scoped and reset at end of session; it is never logged as
-- DDL and never committed.
SELECT set_config('bootstrap.app_pw', :'app_pw', false);

DO $bootstrap$
DECLARE
    v_pw text := current_setting('bootstrap.app_pw');
BEGIN
    IF v_pw IS NULL OR v_pw = '' THEN
        RAISE EXCEPTION 'app_pw is empty; pass it with: psql -v app_pw=...';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE format(
            'CREATE ROLE app_rw LOGIN NOSUPERUSER NOBYPASSRLS '
            'NOCREATEDB NOCREATEROLE PASSWORD %L',
            v_pw
        );
    END IF;
    -- Rotate the password to the supplied secret on every run (idempotent).
    EXECUTE format('ALTER ROLE app_rw WITH PASSWORD %L', v_pw);
END
$bootstrap$;

-- Clear the secret from the session.
SELECT set_config('bootstrap.app_pw', '', false);

-- Let app_rw connect to and resolve names in the public schema. Table/sequence
-- privileges are granted by the 0002_rls migration (and ALTER DEFAULT PRIVILEGES
-- there covers future objects).
GRANT USAGE ON SCHEMA public TO app_rw;
