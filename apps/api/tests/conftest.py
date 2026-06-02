"""Session-scoped fixtures for RLS integration tests.

Spins up an ephemeral ``postgres:16`` Docker container (or reuses an
existing DB via ``TEST_DATABASE_URL``), bootstraps the schema, runs the
0002_rls Alembic migration, seeds deterministic data for two test users,
and exposes a ``Session`` factory connected as ``app_rw``.

Skips gracefully with a clear message when Docker is unavailable and
``TEST_DATABASE_URL`` is not set.

Environment variables (all optional — defaults use the throwaway container):
    TEST_DATABASE_URL: Superuser URL for an already-running Postgres 16.
        When set the container is not started.  Must support ``CREATE ROLE``
        (i.e. needs a superuser or createrole account).
"""

import os
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
_INIT_SQL = os.path.join(_REPO_ROOT, "packages", "db", "init.sql")
_ALEMBIC_DIR = os.path.join(_REPO_ROOT, "packages", "db")

# Hardcoded test-only credentials — never used outside the throwaway container.
_TEST_SUPERUSER = "postgres"
_TEST_SUPERPASSWORD = "testpw"
_TEST_DBNAME = "gymtest"
_APP_ROLE = "app_rw"
_APP_ROLE_PASSWORD = "app_rw_test_pw"

# Deterministic telegram IDs for the two seed users.
USER_A_ID = 100001
USER_B_ID = 100002


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

def _is_docker_available() -> bool:
    """Return True if the ``docker`` CLI is accessible."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _free_port() -> int:
    """Return an OS-assigned free TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_postgres(host: str, port: int, dbname: str, timeout: int = 60) -> None:
    """Block until Postgres accepts real DB connections or raises TimeoutError.

    Uses psycopg2 to test an actual connection (not just TCP) so the check
    succeeds only when Postgres is fully initialized, not just listening.

    Args:
        host: Hostname to probe.
        port: Port to probe.
        dbname: Database name to connect to.
        timeout: Maximum seconds to wait.

    Raises:
        TimeoutError: If Postgres does not become reachable within ``timeout``.
    """
    import psycopg2

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=_TEST_SUPERUSER,
                password=_TEST_SUPERPASSWORD,
                connect_timeout=2,
            )
            conn.close()
            return
        except psycopg2.OperationalError:
            time.sleep(1)
    raise TimeoutError(f"Postgres did not start on {host}:{port} within {timeout}s")


# ---------------------------------------------------------------------------
# Schema / role bootstrap
# ---------------------------------------------------------------------------

def _run_sql_as_superuser(superuser_url: str, sql: str) -> None:
    """Execute raw SQL via a short-lived superuser engine (NullPool).

    Args:
        superuser_url: SQLAlchemy URL for the superuser connection.
        sql: SQL text to execute (may contain multiple statements).
    """
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    eng.dispose()


def _load_init_sql(superuser_url: str) -> None:
    """Run packages/db/init.sql against the test database.

    Args:
        superuser_url: Superuser URL for the target database.
    """
    with open(_INIT_SQL, encoding="utf-8") as f:
        sql = f.read()
    _run_sql_as_superuser(superuser_url, sql)


def _create_app_role(superuser_url: str) -> None:
    """Create (or reuse) the ``app_rw`` role with the test password.

    Mirrors the logic in packages/db/bootstrap/create_app_role.sql without
    requiring psql or the :\\set password substitution mechanism.

    Args:
        superuser_url: Superuser URL (needs CREATEROLE or superuser privilege).
    """
    sql = f"""
        DO $bootstrap$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN
                EXECUTE format(
                    'CREATE ROLE {_APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS '
                    'NOCREATEDB NOCREATEROLE PASSWORD %L',
                    '{_APP_ROLE_PASSWORD}'
                );
            ELSE
                EXECUTE format('ALTER ROLE {_APP_ROLE} WITH PASSWORD %L',
                               '{_APP_ROLE_PASSWORD}');
            END IF;
        END
        $bootstrap$;
        GRANT USAGE ON SCHEMA public TO {_APP_ROLE};
        GRANT CONNECT ON DATABASE {_TEST_DBNAME} TO {_APP_ROLE};
    """
    _run_sql_as_superuser(superuser_url, sql)


def _run_alembic_upgrade(superuser_url: str) -> None:
    """Stamp 0001_baseline then upgrade to head (runs 0002_rls).

    Args:
        superuser_url: Superuser URL passed to Alembic via the
            ``DATABASE_URL`` environment variable (Alembic env.py reads it).

    Raises:
        subprocess.CalledProcessError: If any Alembic command fails.
    """
    env = {**os.environ, "DATABASE_URL": superuser_url}
    for cmd in (
        ["alembic", "stamp", "0001_baseline"],
        ["alembic", "upgrade", "head"],
    ):
        subprocess.run(
            cmd,
            cwd=_ALEMBIC_DIR,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_data(superuser_url: str) -> dict:
    """Insert deterministic two-user seed data and return row counts.

    Inserts:
    - 1 global muscle (chest) + 1 global exercise (bench press)
    - 1 private muscle per user + 1 private exercise per user
    - 2 training rows per user
    - 1 hidden exercise per user (each hides the other's private exercise
      so the hidden-row tests have something to assert against)

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        A mapping of seed counts, e.g. ``{'training_a': 2, ...}``, so tests
        can assert exact expected counts without re-counting from the DB.
    """
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        # Users
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES
                (:a_id, NOW(), 'Alice', 'alice_test'),
                (:b_id, NOW(), 'Bob',   'bob_test')
            ON CONFLICT (id) DO NOTHING
        """), {"a_id": USER_A_ID, "b_id": USER_B_ID})

        # Global muscle
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Global Chest', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        global_muscle_row = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Global Chest' AND created_by IS NULL"
        )).fetchone()
        global_muscle_id = global_muscle_row[0]

        # Global exercise
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Global Bench Press', :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"mid": global_muscle_id})
        global_ex_row = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Global Bench Press'"
        )).fetchone()
        global_ex_id = global_ex_row[0]

        # Private muscle A
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Private Muscle A', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_A_ID})
        priv_muscle_a = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Private Muscle A' AND created_by=:uid"
        ), {"uid": USER_A_ID}).fetchone()[0]

        # Private muscle B
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Private Muscle B', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_B_ID})
        priv_muscle_b = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Private Muscle B' AND created_by=:uid"
        ), {"uid": USER_B_ID}).fetchone()[0]

        # Private exercise A
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Private Ex A', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": priv_muscle_a, "uid": USER_A_ID})
        priv_ex_a = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Private Ex A' AND created_by=:uid"
        ), {"uid": USER_A_ID}).fetchone()[0]

        # Private exercise B
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Private Ex B', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": priv_muscle_b, "uid": USER_B_ID})
        priv_ex_b = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Private Ex B' AND created_by=:uid"
        ), {"uid": USER_B_ID}).fetchone()[0]

        # Training rows — 2 per user
        for i in range(2):
            conn.execute(text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, NOW(), :uid, :mid, :eid, :s, 100.0, 10.0)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "uid": USER_A_ID,
                "mid": priv_muscle_a,
                "eid": priv_ex_a,
                "s": i + 1,
            })
            conn.execute(text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, NOW(), :uid, :mid, :eid, :s, 80.0, 8.0)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "uid": USER_B_ID,
                "mid": priv_muscle_b,
                "eid": priv_ex_b,
                "s": i + 1,
            })

        # Hidden exercises: A hides B's private exercise, B hides A's
        conn.execute(text("""
            INSERT INTO user_hidden_exercises (user_id, exercise_id)
            VALUES (:uid, :eid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_A_ID, "eid": priv_ex_b})

        conn.execute(text("""
            INSERT INTO user_hidden_exercises (user_id, exercise_id)
            VALUES (:uid, :eid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_B_ID, "eid": priv_ex_a})

        conn.commit()
    eng.dispose()

    return {
        "global_muscle_id": global_muscle_id,
        "global_ex_id": global_ex_id,
        "priv_muscle_a": priv_muscle_a,
        "priv_muscle_b": priv_muscle_b,
        "priv_ex_a": priv_ex_a,
        "priv_ex_b": priv_ex_b,
        "training_a": 2,
        "training_b": 2,
        "hidden_ex_a": 1,  # A hides B's exercise
        "hidden_ex_b": 1,
    }


# ---------------------------------------------------------------------------
# Session-scoped fixture: DB container + schema + seed
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_setup():
    """Start (or reuse) a Postgres 16, run migrations, seed data.

    Yields:
        A dict with keys:
            ``superuser_url``: full connection URL for a superuser.
            ``app_rw_url``: connection URL for ``app_rw`` (NOBYPASSRLS).
            ``seed``: mapping returned by ``_seed_data``.

    Skips the entire test session if Docker is unavailable and
    ``TEST_DATABASE_URL`` is not set.
    """
    test_url = os.getenv("TEST_DATABASE_URL")
    container_id: Optional[str] = None
    pg_port: Optional[int] = None

    if test_url:
        # Use the caller-supplied URL directly.
        superuser_url = test_url
    else:
        if not _is_docker_available():
            pytest.skip(
                "Docker is not available and TEST_DATABASE_URL is not set. "
                "Cannot spin up an ephemeral Postgres 16 for RLS tests. "
                "Set TEST_DATABASE_URL=postgresql://superuser:pw@host/db to skip Docker."
            )

        pg_port = _free_port()
        container_name = f"gym_rls_test_{uuid.uuid4().hex[:8]}"

        # Start the container.
        run_result = subprocess.run(
            [
                "docker", "run", "--rm", "-d",
                "--name", container_name,
                "-e", f"POSTGRES_PASSWORD={_TEST_SUPERPASSWORD}",
                "-e", f"POSTGRES_DB={_TEST_DBNAME}",
                "-p", f"{pg_port}:5432",
                "postgres:16",
            ],
            capture_output=True,
            text=True,
        )
        if run_result.returncode != 0:
            pytest.fail(f"Failed to start postgres:16 container: {run_result.stderr}")
        container_id = run_result.stdout.strip()

        try:
            _wait_for_postgres("127.0.0.1", pg_port, _TEST_DBNAME, timeout=60)
        except TimeoutError as exc:
            subprocess.run(["docker", "stop", container_id],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pytest.fail(str(exc))

        superuser_url = (
            f"postgresql://{_TEST_SUPERUSER}:{_TEST_SUPERPASSWORD}"
            f"@127.0.0.1:{pg_port}/{_TEST_DBNAME}"
        )

    # ---- schema + role + migrations ----
    try:
        _load_init_sql(superuser_url)
        _create_app_role(superuser_url)
        _run_alembic_upgrade(superuser_url)
    except Exception as exc:
        if container_id:
            subprocess.run(["docker", "stop", container_id],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pytest.fail(f"DB setup failed: {exc}")

    # ---- seed data ----
    seed = _seed_data(superuser_url)

    # ---- app_rw URL ----
    if test_url:
        # Caller must have already created app_rw; we derive the host/port/db
        # from the superuser URL but swap the credentials.
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(test_url)
        app_rw_url = urlunparse(parsed._replace(
            netloc=f"{_APP_ROLE}:{_APP_ROLE_PASSWORD}@{parsed.hostname}:{parsed.port or 5432}"
        ))
    else:
        app_rw_url = (
            f"postgresql://{_APP_ROLE}:{_APP_ROLE_PASSWORD}"
            f"@127.0.0.1:{pg_port}/{_TEST_DBNAME}"
        )

    yield {
        "superuser_url": superuser_url,
        "app_rw_url": app_rw_url,
        "seed": seed,
    }

    # ---- teardown ----
    if container_id:
        subprocess.run(
            ["docker", "stop", container_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------------------
# Session-scoped fixture: app_rw engine + GUC-wired SessionFactory
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app_rw_session_factory(db_setup):
    """Build a SessionFactory connected as ``app_rw`` with the GUC after_begin event.

    Reuses the ``after_begin`` wiring from ``apps/api/app/core/database.py``
    so the test exercises the exact same code path the production API uses.

    Args:
        db_setup: Session fixture that provides ``app_rw_url``.

    Yields:
        A SQLAlchemy ``sessionmaker`` instance.
    """
    from sqlalchemy.pool import NullPool

    # Import the contextvar accessors from the app — this exercises the real wiring.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.db_context import current_role, current_user_id

    eng = create_engine(db_setup["app_rw_url"], poolclass=NullPool)
    Factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)

    @event.listens_for(Factory, "after_begin")
    def _set_gucs(session: Session, transaction: object, connection: object) -> None:
        uid = current_user_id.get()
        role = current_role.get()
        connection.execute(
            text(
                "SELECT set_config('app.user_id', :uid, true),"
                " set_config('app.role', :role, true)"
            ),
            {"uid": uid, "role": role},
        )

    yield Factory

    eng.dispose()


# ---------------------------------------------------------------------------
# Helper context manager exposed to tests
# ---------------------------------------------------------------------------

@contextmanager
def rls_session(
    factory: sessionmaker,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
) -> Generator[Session, None, None]:
    """Open a Session with the given principal context and close on exit.

    Sets ``current_user_id`` / ``current_role`` contextvars from
    ``app.core.db_context`` so the ``after_begin`` GUC wiring picks them up.

    Args:
        factory: The ``sessionmaker`` to use (must have the after_begin event).
        user_id: Telegram user id to impersonate, or ``None`` for no principal.
        role: ``'user'`` or ``'admin'``, or ``None`` for no role (fail-closed).

    Yields:
        An active ``Session`` with GUCs set for every transaction it begins.
    """
    from app.core.db_context import set_principal_context, reset_principal_context

    uid_token, role_token = set_principal_context(user_id, role)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        reset_principal_context(uid_token, role_token)
