"""GYM-81: Integration tests for rename + delete-guard + is_mine.

Covers:
  1. PATCH /muscles/{id}   — rename own custom muscle.
  2. PATCH /exercises/{id} — rename own custom exercise.
  3. 403 when attempting to rename a global item.
  4. 409 when renaming to a duplicate name (same user).
  5. 422 when the new name is invalid (empty / too long / bad char).
  6. DELETE /muscles/{id}  — 409 when training history exists; 204 when clean.
  7. DELETE /exercises/{id} — 409 when training history exists; 204 when clean.
  8. is_mine: True for caller's own custom item, False for global, in list.

Seed (USER_81_ID = 500081):
  muscle_81:   private muscle owned by USER_81_ID
  muscle_81b:  second private muscle (for dup-name test)
  ex_81:       private exercise under muscle_81, HAS training history
  ex_81_clean: private exercise under muscle_81, NO training history
  muscle_81_clean: private muscle with NO training history on any exercise
    ex_81_under_clean: private exercise under muscle_81_clean, no history
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

USER_81_ID = 500081


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

def _seed_gym81(superuser_url: str) -> dict:
    """Insert seed data for GYM-81 tests.

    Creates:
    - USER_81_ID user row
    - muscle_81: private muscle with a training-bearing exercise
    - muscle_81b: second private muscle (no history, for dup-name test)
    - ex_81: private exercise under muscle_81, WITH training history
    - ex_81_clean: private exercise under muscle_81, NO history
    - muscle_81_clean: private muscle with no history
    - ex_81_under_clean: exercise under muscle_81_clean, no history

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User81', 'user81_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_81_ID})

        # muscle_81
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym81 Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym81 Muscle' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        muscle_81 = row[0]

        # muscle_81b (second muscle for dup-name test, no history)
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym81 Muscle B', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym81 Muscle B' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        muscle_81b = row[0]

        # muscle_81_clean (no history on any of its exercises)
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym81 Clean Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym81 Clean Muscle' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        muscle_81_clean = row[0]

        # ex_81: WITH training history
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym81 Ex With History', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_81, "uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym81 Ex With History' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        ex_81 = row[0]

        # ex_81_clean: NO training history
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym81 Ex Clean', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_81, "uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym81 Ex Clean' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        ex_81_clean = row[0]

        # ex_81_under_clean: under the clean muscle, no history
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym81 Ex Under Clean', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_81_clean, "uid": USER_81_ID})
        row = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym81 Ex Under Clean' AND created_by=:uid"
        ), {"uid": USER_81_ID}).fetchone()
        ex_81_under_clean = row[0]

        # Insert 1 training row referencing ex_81 / muscle_81
        conn.execute(text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 90.0, 10.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "uid": USER_81_ID,
            "mid": muscle_81,
            "eid": ex_81,
        })

        conn.commit()
    eng.dispose()

    return {
        "muscle_81": muscle_81,
        "muscle_81b": muscle_81b,
        "muscle_81_clean": muscle_81_clean,
        "ex_81": ex_81,
        "ex_81_clean": ex_81_clean,
        "ex_81_under_clean": ex_81_under_clean,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym81_client(db_setup) -> Generator:
    """Build a TestClient for GYM-81 tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym81(db_setup["superuser_url"])

    parsed = urlparse(app_rw_url)
    os.environ["APP_DB_USER"] = _APP_ROLE
    os.environ["APP_DB_PASSWORD"] = _APP_ROLE_PASSWORD
    os.environ["DB_HOST"] = parsed.hostname or "127.0.0.1"
    os.environ["DB_PORT"] = str(parsed.port or 5432)
    os.environ["DB_NAME"] = parsed.path.lstrip("/")
    _ensure_env_defaults()

    from app.core.config import get_settings
    get_settings.cache_clear()

    import importlib
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
# 1. Rename own muscle — 200, name normalized
# ---------------------------------------------------------------------------

class TestRenameMuscle:
    def test_rename_own_muscle_ok(self, gym81_client, db_setup):
        """PATCH /muscles/{id} with own muscle returns 200 and updated name."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "  Renamed Muscle 81  "},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == mid
        assert data["name"] == "Renamed Muscle 81"  # normalized

    def test_rename_normalizes_whitespace(self, gym81_client):
        """Name with extra whitespace is normalized (trimmed + collapsed)."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "  Gym81  Muscle  "},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "Gym81 Muscle"

    def test_rename_own_muscle_is_mine_true(self, gym81_client):
        """Renamed muscle response has is_mine=true."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "Gym81 Muscle"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_mine"] is True

    def test_rename_global_muscle_returns_403(self, gym81_client, db_setup):
        """PATCH /muscles/{id} on a global muscle returns 403."""
        client, seed = gym81_client
        global_mid = db_setup["seed"]["global_muscle_id"]
        resp = client.patch(
            f"/api/v1/muscles/{global_mid}",
            json={"name": "Hack Global"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 403, resp.text

    def test_rename_nonexistent_muscle_returns_404(self, gym81_client):
        """PATCH /muscles/{id} for a non-existent id returns 404."""
        client, seed = gym81_client
        resp = client.patch(
            "/api/v1/muscles/9999999",
            json={"name": "Ghost"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 404, resp.text

    def test_rename_to_duplicate_name_returns_409(self, gym81_client):
        """Renaming a muscle to match another own muscle name returns 409."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        # muscle_81b already has name 'Gym81 Muscle B'
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "Gym81 Muscle B"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 409, resp.text

    def test_rename_invalid_name_empty_returns_422(self, gym81_client):
        """Empty name in PATCH /muscles body returns 422."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": ""},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text

    def test_rename_invalid_name_too_long_returns_422(self, gym81_client):
        """Name exceeding 30 chars in PATCH /muscles body returns 422."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "A" * 31},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text

    def test_rename_invalid_name_bad_char_returns_422(self, gym81_client):
        """Name with disallowed char in PATCH /muscles body returns 422."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": "Bad<Char"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# 2. Rename own exercise — 200, name normalized
# ---------------------------------------------------------------------------

class TestRenameExercise:
    def test_rename_own_exercise_ok(self, gym81_client):
        """PATCH /exercises/{id} with own exercise returns 200 and updated name."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "  Renamed Ex 81  "},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == eid
        assert data["name"] == "Renamed Ex 81"  # normalized

    def test_rename_own_exercise_is_mine_true(self, gym81_client):
        """Renamed exercise response has is_mine=true."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "Gym81 Ex Clean"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_mine"] is True

    def test_rename_global_exercise_returns_403(self, gym81_client, db_setup):
        """PATCH /exercises/{id} on a global exercise returns 403."""
        client, seed = gym81_client
        global_eid = db_setup["seed"]["global_ex_id"]
        resp = client.patch(
            f"/api/v1/exercises/{global_eid}",
            json={"name": "Hack Global"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 403, resp.text

    def test_rename_nonexistent_exercise_returns_404(self, gym81_client):
        """PATCH /exercises/{id} for a non-existent id returns 404."""
        client, seed = gym81_client
        resp = client.patch(
            "/api/v1/exercises/9999999",
            json={"name": "Ghost"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 404, resp.text

    def test_rename_exercise_to_duplicate_name_returns_409(self, gym81_client):
        """Renaming an exercise to match another own exercise (same muscle) returns 409."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        # ex_81 has name 'Gym81 Ex With History' (same muscle)
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "Gym81 Ex With History"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 409, resp.text

    def test_rename_exercise_invalid_name_empty_returns_422(self, gym81_client):
        """Empty name in PATCH /exercises body returns 422."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": ""},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text

    def test_rename_exercise_invalid_name_too_long_returns_422(self, gym81_client):
        """Name exceeding 40 chars in PATCH /exercises body returns 422."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "A" * 41},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text

    def test_rename_exercise_invalid_name_bad_char_returns_422(self, gym81_client):
        """Name with disallowed char in PATCH /exercises body returns 422."""
        client, seed = gym81_client
        eid = seed["ex_81_clean"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "Bad{Char}"},
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# 3. Delete-guard: exercise
# ---------------------------------------------------------------------------

class TestDeleteGuardExercise:
    def test_delete_exercise_with_history_returns_409(self, gym81_client):
        """DELETE /exercises/{id} returns 409 when training history exists."""
        client, seed = gym81_client
        eid = seed["ex_81"]
        resp = client.delete(
            f"/api/v1/exercises/{eid}",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 409, resp.text
        assert "history" in resp.json()["detail"].lower()

    def test_delete_exercise_without_history_returns_204(self, gym81_client):
        """DELETE /exercises/{id} returns 204 when no training history."""
        client, seed = gym81_client
        eid = seed["ex_81_under_clean"]
        resp = client.delete(
            f"/api/v1/exercises/{eid}",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 204, resp.text


# ---------------------------------------------------------------------------
# 4. Delete-guard: muscle
# ---------------------------------------------------------------------------

class TestDeleteGuardMuscle:
    def test_delete_muscle_with_history_returns_409(self, gym81_client):
        """DELETE /muscles/{id} returns 409 when an exercise under it has history."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        resp = client.delete(
            f"/api/v1/muscles/{mid}",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 409, resp.text
        assert "history" in resp.json()["detail"].lower()

    def test_delete_muscle_without_history_returns_204(self, gym81_client):
        """DELETE /muscles/{id} returns 204 when no exercise under it has history."""
        client, seed = gym81_client
        mid = seed["muscle_81_clean"]
        resp = client.delete(
            f"/api/v1/muscles/{mid}",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 204, resp.text


# ---------------------------------------------------------------------------
# 5. is_mine on list endpoints
# ---------------------------------------------------------------------------

class TestIsMineOnLists:
    def test_muscles_list_is_mine_true_for_own(self, gym81_client):
        """GET /muscles includes is_mine=true for caller's own custom muscle."""
        client, seed = gym81_client
        resp = client.get("/api/v1/muscles", headers=_service_headers(USER_81_ID))
        assert resp.status_code == 200, resp.text
        muscles = resp.json()
        # Find muscle_81b (own private, still exists — muscle_81 may have been deleted)
        own = [m for m in muscles if m["id"] == seed["muscle_81b"]]
        assert len(own) == 1, f"muscle_81b not found in list: {[m['id'] for m in muscles]}"
        assert own[0]["is_mine"] is True

    def test_muscles_list_is_mine_false_for_global(self, gym81_client, db_setup):
        """GET /muscles includes is_mine=false for global muscles."""
        client, seed = gym81_client
        global_mid = db_setup["seed"]["global_muscle_id"]
        resp = client.get("/api/v1/muscles", headers=_service_headers(USER_81_ID))
        assert resp.status_code == 200, resp.text
        muscles = resp.json()
        global_items = [m for m in muscles if m["id"] == global_mid]
        assert len(global_items) == 1
        assert global_items[0]["is_mine"] is False

    def test_exercises_list_is_mine_true_for_own(self, gym81_client):
        """GET /muscles/{id}/exercises includes is_mine=true for own exercise."""
        client, seed = gym81_client
        mid = seed["muscle_81"]
        eid = seed["ex_81_clean"]
        resp = client.get(
            f"/api/v1/muscles/{mid}/exercises",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        exercises = resp.json()
        own = [e for e in exercises if e["id"] == eid]
        assert len(own) == 1, f"ex_81_clean not found: {[e['id'] for e in exercises]}"
        assert own[0]["is_mine"] is True

    def test_exercises_list_is_mine_false_for_global(self, gym81_client, db_setup):
        """GET /muscles/{id}/exercises includes is_mine=false for global exercises."""
        client, seed = gym81_client
        global_mid = db_setup["seed"]["global_muscle_id"]
        global_eid = db_setup["seed"]["global_ex_id"]
        resp = client.get(
            f"/api/v1/muscles/{global_mid}/exercises",
            headers=_service_headers(USER_81_ID),
        )
        assert resp.status_code == 200, resp.text
        exercises = resp.json()
        global_items = [e for e in exercises if e["id"] == global_eid]
        assert len(global_items) == 1
        assert global_items[0]["is_mine"] is False
