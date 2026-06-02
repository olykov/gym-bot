"""End-to-end HTTP integration tests for RLS context propagation (GYM-37).

These tests use ``fastapi.testclient.TestClient`` against the real FastAPI app
to prove that the RLS GUC context is correctly wired from HTTP auth headers all
the way through to Postgres query results.

Key question proved here (H2): do contextvars set inside a sync generator dep
(``get_principal``) survive the FastAPI dependency→endpoint threadpool hop and
actually constrain what Postgres returns?

FINDING: With the original contextvar-only approach the answer is NO —
``ValueError: Token was created in a different Context`` was raised inside the
``finally`` block of ``get_principal``, proving that the set/reset ran in
different threadpool-copied contexts.  The endpoint body's ``after_begin`` call
ran with an empty GUC, returning 0 rows for all user queries.

SOLUTION (GYM-37): ``session.info`` approach — the principal is stored on the
Session object by ``get_db_for_principal``/``get_db_for_admin``, and
``after_begin`` reads from ``session.info``.  The Session is shared by
reference within one request; threadpool boundaries don't matter.

Test layout
-----------
- ``TestServiceTokenIsolation``: user A sees only A's rows; user B sees only B's.
- ``TestNoAuthFailClosed``: unauthenticated requests see 0 training rows.
- ``TestInvalidAuthFailClosed``: bad credentials return 401.
- ``TestAdminThenUserNoLeak``: admin request followed by user request on the
  same TestClient worker does NOT let the user see admin-wide data.
- ``TestCatalogM4``: no global catalog row has ``is_global AND created_by IS NOT NULL``.

All tests reuse the ``db_setup`` fixture from conftest.py (the same ephemeral
postgres:16 with 0002_rls applied that GYM-36 tests use).  The app's engine is
overridden via ``app.dependency_overrides`` to use the test DB.
"""

import os
import sys
from typing import Generator, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Ensure the app package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, USER_B_ID, _APP_ROLE, _APP_ROLE_PASSWORD


# ---------------------------------------------------------------------------
# Fixture: configure env + build TestClient with test DB
# ---------------------------------------------------------------------------


def _ensure_env_defaults() -> None:
    """Set env vars required by Settings before importing the app.

    Uses ``setdefault`` so existing vars (e.g. from a real .env) are not
    overwritten.
    """
    os.environ.setdefault("DB_USER", "postgres")
    os.environ.setdefault("DB_PASSWORD", "testpw")
    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", "gymtest")
    os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_rls_tests_only")
    os.environ.setdefault("ADMIN_USER", "admin")
    os.environ.setdefault("ADMIN_PASSWORD", "adminpw")
    os.environ.setdefault("BOT_SERVICE_TOKEN", "test_bot_service_token_rls")
    os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost")


@pytest.fixture(scope="module")
def test_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient for the real app, using the ephemeral test DB.

    The app's DB-access dependencies are overridden to use a ``NullPool``
    engine pointed at the test DB.  This exercises the real ``after_begin``
    GUC wiring (``session.info`` approach) end-to-end through HTTP.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        A configured TestClient.
    """
    app_rw_url = db_setup["app_rw_url"]

    # Override individual DB credentials so APP_DATABASE_URL points to the
    # test DB.  Must be set before ``get_settings()`` is called.
    from urllib.parse import urlparse
    parsed = urlparse(app_rw_url)
    os.environ["APP_DB_USER"] = _APP_ROLE
    os.environ["APP_DB_PASSWORD"] = _APP_ROLE_PASSWORD
    os.environ["DB_HOST"] = parsed.hostname or "127.0.0.1"
    os.environ["DB_PORT"] = str(parsed.port or 5432)
    os.environ["DB_NAME"] = parsed.path.lstrip("/")
    _ensure_env_defaults()

    # Clear the lru_cache so Settings reads the new env vars.
    from app.core.config import get_settings
    get_settings.cache_clear()

    # Import database module AFTER clearing the cache so the engine uses the
    # test URL.  We need to reload the module-level singletons.
    import importlib
    import app.core.database as db_module
    # Rebuild the engine and SessionLocal for the test DB.
    test_engine = create_engine(app_rw_url, poolclass=NullPool)
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    # Register the real after_begin listener on the test session factory.
    from app.core.database import _set_rls_gucs
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    # Swap in the test session factory for the duration of this fixture.
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    # Import the FastAPI app AFTER the engine swap.
    from main import app

    # Override the BOT_SERVICE_TOKEN for auth validation inside the app.
    # (Settings is re-read from env on each get_settings() call after cache clear.)

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Teardown.
    db_module.SessionLocal = original_session_local
    test_engine.dispose()


def _service_headers(user_id: int) -> dict:
    """Build service-token auth headers for user impersonation.

    Args:
        user_id: Telegram user id to act as.

    Returns:
        Header dict with X-Service-Token and X-Act-As-User.
    """
    return {
        "X-Service-Token": "test_bot_service_token_rls",
        "X-Act-As-User": str(user_id),
    }


def _admin_jwt() -> str:
    """Mint an admin JWT using the test JWT_SECRET.

    Returns:
        Signed JWT token string with role='admin'.
    """
    from app.core.auth import create_session_token
    return create_session_token({"id": "admin", "auth_type": "password"})


# ---------------------------------------------------------------------------
# 1. Service-token isolation: user A sees only A's rows
# ---------------------------------------------------------------------------


class TestServiceTokenIsolation:
    """User A and user B see only their own training records via service-token auth."""

    def test_user_a_sees_own_training(self, test_client, db_setup):
        """GET /api/v1/training as user A returns exactly A's training rows.

        This is the core H2 proof: with session.info wiring, Postgres gets
        user_id=A GUC for every transaction and returns exactly A's rows.
        If this returns 0 rows, the session.info wiring is broken.
        """
        seed = db_setup["seed"]
        resp = test_client.get("/api/v1/training", headers=_service_headers(USER_A_ID))
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        rows = resp.json()
        assert len(rows) == seed["training_a"], (
            f"User A should see {seed['training_a']} training rows but got {len(rows)}. "
            "If 0: session.info GUC wiring is not propagating to the DB transaction."
        )
        for row in rows:
            assert row["user_id"] == USER_A_ID, (
                f"User A received a training row with user_id={row['user_id']} "
                f"(should be {USER_A_ID})"
            )

    def test_user_b_sees_own_training(self, test_client, db_setup):
        """GET /api/v1/training as user B returns exactly B's training rows."""
        seed = db_setup["seed"]
        resp = test_client.get("/api/v1/training", headers=_service_headers(USER_B_ID))
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == seed["training_b"], (
            f"User B should see {seed['training_b']} training rows but got {len(rows)}."
        )
        for row in rows:
            assert row["user_id"] == USER_B_ID

    def test_user_a_muscles_includes_own_private(self, test_client, db_setup):
        """GET /api/v1/muscles as user A includes A's private muscle."""
        seed = db_setup["seed"]
        resp = test_client.get("/api/v1/muscles", headers=_service_headers(USER_A_ID))
        assert resp.status_code == 200
        muscle_ids = [m["id"] for m in resp.json()]
        assert seed["priv_muscle_a"] in muscle_ids, (
            f"User A's private muscle (id={seed['priv_muscle_a']}) not in response: {muscle_ids}"
        )

    def test_user_a_muscles_excludes_b_private(self, test_client, db_setup):
        """GET /api/v1/muscles as user A does NOT include B's private muscle."""
        seed = db_setup["seed"]
        resp = test_client.get("/api/v1/muscles", headers=_service_headers(USER_A_ID))
        assert resp.status_code == 200
        muscle_ids = [m["id"] for m in resp.json()]
        assert seed["priv_muscle_b"] not in muscle_ids, (
            f"Cross-tenant leak: user A can see B's private muscle (id={seed['priv_muscle_b']})"
        )

    def test_user_b_muscles_excludes_a_private(self, test_client, db_setup):
        """GET /api/v1/muscles as user B does NOT include A's private muscle."""
        seed = db_setup["seed"]
        resp = test_client.get("/api/v1/muscles", headers=_service_headers(USER_B_ID))
        assert resp.status_code == 200
        muscle_ids = [m["id"] for m in resp.json()]
        assert seed["priv_muscle_a"] not in muscle_ids, (
            f"Cross-tenant leak: user B can see A's private muscle (id={seed['priv_muscle_a']})"
        )

    def test_user_a_training_rows_have_correct_user_id(self, test_client, db_setup):
        """Every training row returned to user A has user_id == USER_A_ID."""
        resp = test_client.get("/api/v1/training", headers=_service_headers(USER_A_ID))
        assert resp.status_code == 200
        for row in resp.json():
            assert row["user_id"] == USER_A_ID


# ---------------------------------------------------------------------------
# 2. No / invalid auth → fail-closed
# ---------------------------------------------------------------------------


class TestNoAuthFailClosed:
    """Requests with no auth credentials should be rejected (401)."""

    def test_no_auth_training_returns_401(self, test_client):
        """GET /api/v1/training with no auth returns 401."""
        resp = test_client.get("/api/v1/training")
        assert resp.status_code == 401, (
            f"Expected 401 with no auth, got {resp.status_code}: {resp.text}"
        )

    def test_no_auth_muscles_returns_401(self, test_client):
        """GET /api/v1/muscles with no auth returns 401."""
        resp = test_client.get("/api/v1/muscles")
        assert resp.status_code == 401


class TestInvalidAuthFailClosed:
    """Requests with invalid credentials should be rejected."""

    def test_bad_service_token_returns_401(self, test_client):
        """X-Service-Token with wrong value returns 401."""
        resp = test_client.get(
            "/api/v1/training",
            headers={"X-Service-Token": "bad-token", "X-Act-As-User": str(USER_A_ID)},
        )
        assert resp.status_code == 401

    def test_service_token_missing_act_as_returns_400(self, test_client):
        """Valid X-Service-Token but no X-Act-As-User returns 400."""
        resp = test_client.get(
            "/api/v1/training",
            headers={"X-Service-Token": "test_bot_service_token_rls"},
        )
        assert resp.status_code == 400

    def test_invalid_bearer_returns_401(self, test_client):
        """Malformed Bearer token returns 401."""
        resp = test_client.get(
            "/api/v1/training",
            headers={"Authorization": "Bearer not_a_real_jwt"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. Admin-then-user no-leak (H1 / H2 reset proof)
# ---------------------------------------------------------------------------


class TestAdminThenUserNoLeak:
    """Admin request followed by user request on the same client must not leak.

    With session.info, each request gets a fresh Session whose info is
    populated from its own principal.  The Session is discarded at request end,
    so no state can leak to the next request on a reused worker.
    """

    def test_admin_then_user_a_sees_only_own_training(self, test_client, db_setup):
        """After an admin list-training call, user A sees only A's own rows.

        The admin request uses the /admin/training endpoint (which requires
        role='admin' and uses get_db_for_admin).  After this request, a
        subsequent user A request on the same TestClient must not receive admin-
        scoped rows — proving that session.info state does not leak across
        request boundaries.
        """
        seed = db_setup["seed"]
        admin_token = _admin_jwt()

        # Admin request: use the /admin/training endpoint (get_db_for_admin path).
        admin_resp = test_client.get(
            "/api/v1/admin/training",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_resp.status_code == 200, (
            f"Admin /admin/training expected 200, got {admin_resp.status_code}: {admin_resp.text}"
        )
        admin_rows = admin_resp.json()
        assert len(admin_rows) >= seed["training_a"] + seed["training_b"], (
            f"Admin should see at least {seed['training_a'] + seed['training_b']} rows, "
            f"got {len(admin_rows)}"
        )

        # Immediately after: user A request on bot-facing endpoint must see only A's rows.
        user_a_resp = test_client.get(
            "/api/v1/training",
            headers=_service_headers(USER_A_ID),
        )
        assert user_a_resp.status_code == 200
        user_a_rows = user_a_resp.json()
        assert len(user_a_rows) == seed["training_a"], (
            f"After admin request, user A should see exactly {seed['training_a']} rows "
            f"but got {len(user_a_rows)}. Stale admin context may have leaked."
        )
        for row in user_a_rows:
            assert row["user_id"] == USER_A_ID

    def test_user_a_then_user_b_no_cross_leak(self, test_client, db_setup):
        """User A request followed by user B request: each sees only own rows."""
        seed = db_setup["seed"]

        resp_a = test_client.get("/api/v1/training", headers=_service_headers(USER_A_ID))
        assert resp_a.status_code == 200
        assert len(resp_a.json()) == seed["training_a"]

        resp_b = test_client.get("/api/v1/training", headers=_service_headers(USER_B_ID))
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == seed["training_b"]


# ---------------------------------------------------------------------------
# 4. M4 data guard: no global row with is_global AND created_by IS NOT NULL
# ---------------------------------------------------------------------------


class TestCatalogM4DataGuard:
    """Pre-deploy data integrity check: global catalog rows must have created_by IS NULL.

    The catalog write policy keeps global rows admin-only ONLY if every
    ``is_global`` row has ``created_by IS NULL``.  If any global row has a
    non-null ``created_by``, the write policy would incorrectly allow the
    owner to modify what should be a shared-catalog item.
    """

    def test_no_global_muscle_with_created_by(self, db_setup):
        """No muscle row has both is_global=TRUE and created_by IS NOT NULL."""
        superuser_url = db_setup["superuser_url"]
        eng = create_engine(superuser_url, poolclass=NullPool)
        with eng.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM muscles "
                    "WHERE is_global AND created_by IS NOT NULL"
                )
            ).scalar()
        eng.dispose()
        assert count == 0, (
            f"Found {count} muscle row(s) with is_global=TRUE and created_by IS NOT NULL. "
            "Global catalog rows must have created_by IS NULL for the write policy to work."
        )

    def test_no_global_exercise_with_created_by(self, db_setup):
        """No exercise row has both is_global=TRUE and created_by IS NOT NULL."""
        superuser_url = db_setup["superuser_url"]
        eng = create_engine(superuser_url, poolclass=NullPool)
        with eng.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM exercises "
                    "WHERE is_global AND created_by IS NOT NULL"
                )
            ).scalar()
        eng.dispose()
        assert count == 0, (
            f"Found {count} exercise row(s) with is_global=TRUE and created_by IS NOT NULL. "
            "Global catalog rows must have created_by IS NULL for the write policy to work."
        )
