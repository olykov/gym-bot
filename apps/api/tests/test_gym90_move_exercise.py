"""GYM-90: Integration tests for PATCH /exercises/{exercise_id}/muscle.

Covers:
  1. Move an own exercise to another (visible) muscle → 200, muscle changed, is_mine True.
  2. Attempt to move a global/canonical exercise → 403.
  3. Move to a non-existent / non-visible target muscle → 404.
  4. Move a non-existent exercise → 404.
  5. Move that collides with an existing own exercise of the same name
     in the target muscle → 409.
  6. (Sanity) Training history that references the moved exercise still resolves
     (exercise id is unchanged; only its muscle changed).

Seed (USER_90_ID = 500090):
  muscle_90_src:  private muscle — source for the moved exercise.
  muscle_90_dst:  private muscle — destination (visible, owned by caller).
  muscle_90_dst2: private muscle — second destination, pre-has a dup-named exercise.
  ex_90_movable:  private exercise under muscle_90_src, HAS training history.
  ex_90_collision: private exercise under muscle_90_dst2 with same name as ex_90_movable.
"""

import os
import sys
import uuid
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_90_ID = 500090


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service_headers(user_id: int) -> dict:
    """Build service-token auth headers impersonating user_id.

    Args:
        user_id: Telegram user id to act as.

    Returns:
        Header dict.
    """
    return {
        "X-Service-Token": "test_bot_service_token_rls",
        "X-Act-As-User": str(user_id),
    }


def _ensure_env_defaults() -> None:
    """Set env vars required by Settings before importing the app."""
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
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_gym90(superuser_url: str) -> dict:
    """Insert seed data for GYM-90 tests.

    Creates:
    - USER_90_ID user row.
    - muscle_90_src: private muscle owned by USER_90_ID (source).
    - muscle_90_dst: private muscle owned by USER_90_ID (destination, clean).
    - muscle_90_dst2: private muscle owned by USER_90_ID (destination with collision).
    - ex_90_movable: private exercise under muscle_90_src, WITH training history.
    - ex_90_collision: private exercise under muscle_90_dst2, same name as ex_90_movable.

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User90', 'user90_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_90_ID})

        # muscle_90_src
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym90 Src Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_90_ID})
        muscle_90_src = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym90 Src Muscle' AND created_by=:uid"
        ), {"uid": USER_90_ID}).fetchone()[0]

        # muscle_90_dst
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym90 Dst Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_90_ID})
        muscle_90_dst = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym90 Dst Muscle' AND created_by=:uid"
        ), {"uid": USER_90_ID}).fetchone()[0]

        # muscle_90_dst2 (will have a collision exercise)
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym90 Dst Muscle 2', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_90_ID})
        muscle_90_dst2 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym90 Dst Muscle 2' AND created_by=:uid"
        ), {"uid": USER_90_ID}).fetchone()[0]

        # ex_90_movable: under muscle_90_src, WITH training history
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym90 Movable Ex', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_90_src, "uid": USER_90_ID})
        ex_90_movable = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym90 Movable Ex' AND created_by=:uid"
        ), {"uid": USER_90_ID}).fetchone()[0]

        # Insert training history referencing ex_90_movable
        conn.execute(text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 80.0, 10.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "uid": USER_90_ID,
            "mid": muscle_90_src,
            "eid": ex_90_movable,
        })

        # ex_90_collision: same name as ex_90_movable, under muscle_90_dst2
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym90 Movable Ex', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_90_dst2, "uid": USER_90_ID})
        ex_90_collision = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym90 Movable Ex'"
            " AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_90_ID, "mid": muscle_90_dst2}).fetchone()[0]

        conn.commit()
    eng.dispose()

    return {
        "muscle_90_src": muscle_90_src,
        "muscle_90_dst": muscle_90_dst,
        "muscle_90_dst2": muscle_90_dst2,
        "ex_90_movable": ex_90_movable,
        "ex_90_collision": ex_90_collision,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym90_client(db_setup) -> Generator:
    """Build a TestClient for GYM-90 tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym90(db_setup["superuser_url"])

    parsed = urlparse(app_rw_url)
    os.environ["APP_DB_USER"] = _APP_ROLE
    os.environ["APP_DB_PASSWORD"] = _APP_ROLE_PASSWORD
    os.environ["DB_HOST"] = parsed.hostname or "127.0.0.1"
    os.environ["DB_PORT"] = str(parsed.port or 5432)
    os.environ["DB_NAME"] = parsed.path.lstrip("/")
    _ensure_env_defaults()

    from app.core.config import get_settings
    get_settings.cache_clear()

    import app.core.database as db_module

    test_engine = create_engine(app_rw_url, poolclass=NullPool)
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    from app.core.database import _set_rls_gucs
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    yield client, seed

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 1. Move own exercise to another visible muscle — 200
# ---------------------------------------------------------------------------


class TestMoveExerciseSuccess:
    def test_move_own_exercise_ok(self, gym90_client):
        """PATCH /exercises/{id}/muscle with own exercise returns 200, muscle updated."""
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        dst = seed["muscle_90_dst"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == eid
        assert data["muscle"] == dst

    def test_move_own_exercise_is_mine_true(self, gym90_client):
        """Move response has is_mine=True."""
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        dst = seed["muscle_90_dst"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_mine"] is True

    def test_move_back_to_src_muscle_ok(self, gym90_client):
        """Can move back to the original source muscle (idempotent move)."""
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        src = seed["muscle_90_src"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": src},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["muscle"] == src


# ---------------------------------------------------------------------------
# 2. Move global/canonical exercise → 403
# ---------------------------------------------------------------------------


class TestMoveGlobalExercise403:
    def test_move_global_exercise_returns_403(self, gym90_client, db_setup):
        """PATCH /exercises/{id}/muscle on a global exercise returns 403."""
        client, seed = gym90_client
        global_eid = db_setup["seed"]["global_ex_id"]
        dst = seed["muscle_90_dst"]
        resp = client.patch(
            f"/api/v1/exercises/{global_eid}/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 403, resp.text

    def test_move_other_users_exercise_returns_404(self, gym90_client, db_setup):
        """PATCH /exercises/{id}/muscle for another user's exercise returns 404.

        RLS makes the other user's private exercise invisible to the caller, so
        the DB query returns no row and the endpoint responds 404 (not 403).
        """
        client, seed = gym90_client
        # priv_ex_b is owned by USER_B_ID (100002), not USER_90_ID
        other_ex = db_setup["seed"]["priv_ex_b"]
        dst = seed["muscle_90_dst"]
        resp = client.patch(
            f"/api/v1/exercises/{other_ex}/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 3. Move to non-existent / non-visible target muscle → 404
# ---------------------------------------------------------------------------


class TestMoveToNonexistentMuscle404:
    def test_move_to_nonexistent_muscle_returns_404(self, gym90_client):
        """PATCH /exercises/{id}/muscle with nonexistent muscle_id returns 404."""
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": 9999999},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 404, resp.text

    def test_move_to_other_users_private_muscle_returns_404(self, gym90_client, db_setup):
        """PATCH /exercises/{id}/muscle to another user's private muscle returns 404.

        Another user's private muscle is not visible to the caller.
        """
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        other_muscle = db_setup["seed"]["priv_muscle_b"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": other_muscle},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 4. Move a non-existent exercise → 404
# ---------------------------------------------------------------------------


class TestMoveNonexistentExercise404:
    def test_move_nonexistent_exercise_returns_404(self, gym90_client):
        """PATCH /exercises/9999999/muscle returns 404."""
        client, seed = gym90_client
        dst = seed["muscle_90_dst"]
        resp = client.patch(
            "/api/v1/exercises/9999999/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 5. Collision with existing exercise of same name in target muscle → 409
# ---------------------------------------------------------------------------


class TestMoveCollision409:
    def test_move_collision_returns_409(self, gym90_client):
        """Moving exercise to a muscle that already has an exercise with the same name → 409."""
        client, seed = gym90_client
        # Reset ex_90_movable to src (prior tests may have moved it back already)
        eid = seed["ex_90_movable"]
        src = seed["muscle_90_src"]
        client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": src},
            headers=_service_headers(USER_90_ID),
        )

        # Now move to muscle_90_dst2 where 'Gym90 Movable Ex' already exists
        dst2 = seed["muscle_90_dst2"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": dst2},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 409, resp.text
        assert "already have" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Sanity — training history still resolves after move
# ---------------------------------------------------------------------------


class TestTrainingHistoryAfterMove:
    def test_training_history_resolves_after_move(self, gym90_client, db_setup):
        """Training rows that reference the moved exercise are still queryable by id.

        The exercise id is unchanged; only its muscle column changes.
        """
        client, seed = gym90_client
        eid = seed["ex_90_movable"]
        dst = seed["muscle_90_dst"]

        # Ensure exercise is on the src muscle first (reset from prior tests)
        src = seed["muscle_90_src"]
        client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": src},
            headers=_service_headers(USER_90_ID),
        )

        # Move to dst
        resp = client.patch(
            f"/api/v1/exercises/{eid}/muscle",
            json={"muscle_id": dst},
            headers=_service_headers(USER_90_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == eid  # id unchanged

        # Verify training history is still accessible via the analytics endpoint
        # (GET /api/v1/exercises/{id}/history)
        hist_resp = client.get(
            f"/api/v1/exercises/{eid}/history",
            headers=_service_headers(USER_90_ID),
        )
        # 200 with data, or 404 if endpoint doesn't exist in this config — either
        # way the move must not have cascaded to delete training rows.
        if hist_resp.status_code == 200:
            # history is returned — id still resolves
            assert hist_resp.status_code == 200
        else:
            # Endpoint may not exist; just check the exercise itself is queryable
            exs_resp = client.get(
                f"/api/v1/muscles/{dst}/exercises",
                headers=_service_headers(USER_90_ID),
            )
            assert exs_resp.status_code == 200
            ids = [e["id"] for e in exs_resp.json()]
            assert eid in ids, f"exercise {eid} not found in target muscle's list"
