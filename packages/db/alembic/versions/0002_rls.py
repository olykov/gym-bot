"""row-level security: helpers, policies, GRANTs to app_rw

Revision ID: 0002_rls
Revises: 0001_baseline
Create Date: 2026-06-02 00:30:00.000000+00:00

GYM-32 — Phase 4 Postgres RLS.

This migration installs DB-enforced, fail-closed per-user isolation. It does
NOT create the app role (that is the infra bootstrap,
packages/db/bootstrap/create_app_role.sql, run by GYM-34); the migration only:

  1. defines two re-runnable PL/pgSQL helper functions that ENABLE + FORCE RLS
     and create the four standard CRUD policies on a table:
       * enable_user_rls(table, owner_col)  — user-owned tables
       * enable_catalog_rls(table)          — is_global/created_by catalog tables
  2. applies them to the six base tables, and
  3. GRANTs CRUD on all tables + USAGE/SELECT on all sequences to app_rw
     (conditionally — skipped if the role does not exist yet so dev DBs work),
     and sets ALTER DEFAULT PRIVILEGES so future tables/sequences inherit them.

Request context (set by the API per transaction via SET LOCAL):
  * app.user_id — bigint as text; owner key comparison
  * app.role    — 'user' | 'admin'; admin branch bypasses the owner check

Fail-closed read template (empty string / unset → NULL → matches no row):
  nullif(current_setting('app.user_id', true), '')::bigint

IMPORTANT: RLS is ignored by superusers and by roles with BYPASSRLS. The app
must connect as app_rw (NOSUPERUSER NOBYPASSRLS) for these policies to take
effect; the legacy superuser `myuser` still bypasses them (kept for ops/migrations).

Backward compatibility: no schema/data change — only RLS + GRANTs. Existing
clients connecting as the superuser are unaffected. downgrade() is fully
symmetric (drops policies, NO FORCE + DISABLE RLS, REVOKEs, drops helpers).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_rls"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The non-superuser role the API connects as. Must match the infra bootstrap
# (packages/db/bootstrap/create_app_role.sql) and GYM-33/GYM-34.
APP_ROLE = "app_rw"

# Tables RLS is applied to, in a fixed order. Used by downgrade() to drop
# policies / disable RLS symmetrically.
USER_TABLES = (
    ("users", "id"),  # owner key is the telegram id itself
    ("training", "user_id"),
    ("user_hidden_muscles", "user_id"),
    ("user_hidden_exercises", "user_id"),
)
CATALOG_TABLES = ("muscles", "exercises")

# Policy name suffixes created by the helpers (per command).
_USER_POLICIES = (
    ("rls_user_select", "SELECT"),
    ("rls_user_insert", "INSERT"),
    ("rls_user_update", "UPDATE"),
    ("rls_user_delete", "DELETE"),
)
_CATALOG_POLICIES = (
    ("rls_catalog_select", "SELECT"),
    ("rls_catalog_insert", "INSERT"),
    ("rls_catalog_update", "UPDATE"),
    ("rls_catalog_delete", "DELETE"),
)


# --- PL/pgSQL helper bodies ----------------------------------------------
# Both helpers are idempotent: every policy is DROP POLICY IF EXISTS'd before
# CREATE, and ENABLE/FORCE RLS are no-ops if already set, so re-running them
# (and re-running this migration after a partial failure) is safe.

_ENABLE_USER_RLS = r"""
CREATE OR REPLACE FUNCTION public.enable_user_rls(p_table regclass, p_owner_col text)
RETURNS void
LANGUAGE plpgsql
AS $func$
DECLARE
    v_owner text := quote_ident(p_owner_col);
    -- Fail-closed owner predicate: unset/empty app.user_id -> NULL -> no match.
    -- Admin branch lets a request with app.role='admin' see/modify all rows.
    v_predicate text := format(
        '(%s = nullif(current_setting(''app.user_id'', true), '''')::bigint'
        ' OR current_setting(''app.role'', true) = ''admin'')',
        v_owner
    );
BEGIN
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', p_table);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', p_table);

    EXECUTE format('DROP POLICY IF EXISTS rls_user_select ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_user_select ON %s AS PERMISSIVE FOR SELECT USING %s',
        p_table, v_predicate
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_user_insert ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_user_insert ON %s AS PERMISSIVE FOR INSERT WITH CHECK %s',
        p_table, v_predicate
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_user_update ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_user_update ON %s AS PERMISSIVE FOR UPDATE USING %s WITH CHECK %s',
        p_table, v_predicate, v_predicate
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_user_delete ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_user_delete ON %s AS PERMISSIVE FOR DELETE USING %s',
        p_table, v_predicate
    );
END;
$func$;
"""

_ENABLE_CATALOG_RLS = r"""
CREATE OR REPLACE FUNCTION public.enable_catalog_rls(p_table regclass)
RETURNS void
LANGUAGE plpgsql
AS $func$
DECLARE
    -- SELECT: global rows are visible to everyone; private rows only to owner.
    v_read text := '(is_global'
        ' OR created_by = nullif(current_setting(''app.user_id'', true), '''')::bigint'
        ' OR current_setting(''app.role'', true) = ''admin'')';
    -- Writes: only own rows. Global rows have created_by IS NULL, so the owner
    -- comparison is NULL (never true) -> only app.role='admin' can write them.
    v_write text := '(created_by = nullif(current_setting(''app.user_id'', true), '''')::bigint'
        ' OR current_setting(''app.role'', true) = ''admin'')';
BEGIN
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', p_table);
    EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', p_table);

    EXECUTE format('DROP POLICY IF EXISTS rls_catalog_select ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_catalog_select ON %s AS PERMISSIVE FOR SELECT USING %s',
        p_table, v_read
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_catalog_insert ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_catalog_insert ON %s AS PERMISSIVE FOR INSERT WITH CHECK %s',
        p_table, v_write
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_catalog_update ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_catalog_update ON %s AS PERMISSIVE FOR UPDATE USING %s WITH CHECK %s',
        p_table, v_write, v_write
    );

    EXECUTE format('DROP POLICY IF EXISTS rls_catalog_delete ON %s', p_table);
    EXECUTE format(
        'CREATE POLICY rls_catalog_delete ON %s AS PERMISSIVE FOR DELETE USING %s',
        p_table, v_write
    );
END;
$func$;
"""

# GRANT/REVOKE are wrapped so the migration succeeds on a dev DB where app_rw
# was never created. On prod the infra bootstrap creates the role first.
_GRANT_APP_RW = f"""
DO $do$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE};
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE};
    ELSE
        RAISE NOTICE
            'Role {APP_ROLE} does not exist; skipping GRANTs. '
            'Run packages/db/bootstrap/create_app_role.sql first (infra GYM-34).';
    END IF;
END
$do$;
"""

_REVOKE_APP_RW = f"""
DO $do$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE};
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE USAGE, SELECT ON SEQUENCES FROM {APP_ROLE};
        REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {APP_ROLE};
        REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE};
    END IF;
END
$do$;
"""


def upgrade() -> None:
    """Install RLS helpers, apply policies to the six base tables, GRANT to app_rw."""
    # 1. Re-runnable helper functions.
    op.execute(_ENABLE_USER_RLS)
    op.execute(_ENABLE_CATALOG_RLS)

    # 2. Apply RLS. One line per table — the convention future tables follow.
    for table, owner_col in USER_TABLES:
        op.execute(f"SELECT public.enable_user_rls('{table}', '{owner_col}')")
    for table in CATALOG_TABLES:
        op.execute(f"SELECT public.enable_catalog_rls('{table}')")

    # 3. Grant the app role CRUD + sequence access (conditional on its existence).
    op.execute(_GRANT_APP_RW)


def downgrade() -> None:
    """Fully reverse upgrade(): drop policies, disable RLS, revoke, drop helpers."""
    # 1. Revoke first (before dropping anything the role was granted on).
    op.execute(_REVOKE_APP_RW)

    # 2. Drop policies + NO FORCE + DISABLE RLS on every table.
    for table, _owner_col in USER_TABLES:
        for policy, _cmd in _USER_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in CATALOG_TABLES:
        for policy, _cmd in _CATALOG_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # 3. Drop helper functions.
    op.execute("DROP FUNCTION IF EXISTS public.enable_catalog_rls(regclass)")
    op.execute("DROP FUNCTION IF EXISTS public.enable_user_rls(regclass, text)")
