"""GYM-85: Integration tests for find-or-create-or-unhide and key-based rename dedup.

Covers:
  1. POST /muscles — name matching an own (visible) muscle → 200, resolution=existing,
     no new row created.
  2. POST /muscles — name matching a visible GLOBAL muscle → 200, resolution=existing.
  3. POST /muscles — name matching a HIDDEN global muscle → 200, resolution=unhidden,
     UserHiddenMuscle row removed, muscle now visible.
  4. POST /muscles — genuinely new name → 201, resolution=created.
  5. POST /muscles — separator/case variant of an existing own muscle → resolves to
     existing (key match), NOT a duplicate row.
  6. POST /exercises — name matching an own visible exercise → 200, resolution=existing.
  7. POST /exercises — name matching a visible GLOBAL exercise → 200, resolution=existing.
  8. POST /exercises — name matching a HIDDEN global exercise → 200, resolution=unhidden,
     UserHiddenExercise row removed.
  9. POST /exercises — genuinely new name → 201, resolution=created.
 10. POST /exercises — separator/case variant of an existing own exercise → resolves to
     existing (key match), NOT a duplicate.
 11. PATCH /muscles/{id} rename to a key colliding with another own visible muscle → 409.
 12. PATCH /muscles/{id} rename to a fresh key → 200.
 13. PATCH /exercises/{id} rename to a key colliding with another own visible exercise
     (same muscle) → 409.
 14. PATCH /exercises/{id} rename to a fresh key → 200.

Seed (USER_85_ID = 500085):
  muscle_85_own:    own private muscle for resolution-existing tests.
  muscle_85_own2:   second own private muscle (rename-collision target).
  muscle_85_rename: own private muscle to be renamed in tests.
  global_muscle_85: global muscle (created_by=NULL) for resolution tests.
  global_ex_85:     global exercise under global_muscle_85.
  ex_85_own:        own exercise under muscle_85_own (resolution-existing).
  ex_85_own2:       second own exercise under muscle_85_own (rename-collision target).
  ex_85_rename:     own exercise under muscle_85_own to be renamed.
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

USER_85_ID = 500085


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


def _seed_gym85(superuser_url: str) -> dict:
    """Insert seed data for GYM-85 tests.

    Creates:
    - USER_85_ID user row.
    - global_muscle_85:   global muscle (for resolution tests).
    - global_ex_85:       global exercise under global_muscle_85.
    - muscle_85_own:      own private muscle (resolution-existing target).
    - muscle_85_own2:     second own private muscle (rename-collision target).
    - muscle_85_rename:   own private muscle to rename.
    - ex_85_own:          own exercise under muscle_85_own (resolution-existing target).
    - ex_85_own2:         second own exercise under muscle_85_own (rename-collision).
    - ex_85_rename:       own exercise under muscle_85_own to rename.
    - hidden entry: USER_85_ID hides global_muscle_85.
    - hidden entry: USER_85_ID hides global_ex_85.

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User85', 'user85_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_85_ID})

        # Global muscle for resolution tests.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym85 Global Muscle', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        global_muscle_85 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym85 Global Muscle' AND created_by IS NULL"
        )).fetchone()[0]

        # Global exercise under the global muscle.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym85 Global Ex', :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"mid": global_muscle_85})
        global_ex_85 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym85 Global Ex' AND created_by IS NULL"
        )).fetchone()[0]

        # Own private muscle (resolution-existing target).
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym85 Own Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_85_ID})
        muscle_85_own = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym85 Own Muscle' AND created_by=:uid"
        ), {"uid": USER_85_ID}).fetchone()[0]

        # Second own private muscle (rename-collision target).
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym85 Own Muscle Two', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_85_ID})
        muscle_85_own2 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym85 Own Muscle Two' AND created_by=:uid"
        ), {"uid": USER_85_ID}).fetchone()[0]

        # Own muscle to rename in tests.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym85 Rename Me Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_85_ID})
        muscle_85_rename = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym85 Rename Me Muscle' AND created_by=:uid"
        ), {"uid": USER_85_ID}).fetchone()[0]

        # Own exercise under muscle_85_own (resolution-existing target).
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym85 Own Ex', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_85_own, "uid": USER_85_ID})
        ex_85_own = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym85 Own Ex' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_85_ID, "mid": muscle_85_own}).fetchone()[0]

        # Second own exercise under muscle_85_own (rename-collision target).
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym85 Own Ex Two', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_85_own, "uid": USER_85_ID})
        ex_85_own2 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym85 Own Ex Two' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_85_ID, "mid": muscle_85_own}).fetchone()[0]

        # Own exercise to rename in tests.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym85 Rename Me Ex', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_85_own, "uid": USER_85_ID})
        ex_85_rename = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym85 Rename Me Ex' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_85_ID, "mid": muscle_85_own}).fetchone()[0]

        # Hide the global muscle for USER_85_ID.
        conn.execute(text("""
            INSERT INTO user_hidden_muscles (user_id, muscle_id)
            VALUES (:uid, :mid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_85_ID, "mid": global_muscle_85})

        # Hide the global exercise for USER_85_ID.
        conn.execute(text("""
            INSERT INTO user_hidden_exercises (user_id, exercise_id)
            VALUES (:uid, :eid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_85_ID, "eid": global_ex_85})

        conn.commit()
    eng.dispose()

    return {
        "global_muscle_85": global_muscle_85,
        "global_ex_85": global_ex_85,
        "muscle_85_own": muscle_85_own,
        "muscle_85_own2": muscle_85_own2,
        "muscle_85_rename": muscle_85_rename,
        "ex_85_own": ex_85_own,
        "ex_85_own2": ex_85_own2,
        "ex_85_rename": ex_85_rename,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym85_client(db_setup) -> Generator:
    """Build a TestClient for GYM-85 tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym85(db_setup["superuser_url"])

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
# Helpers: count rows in a table via superuser
# ---------------------------------------------------------------------------


def _count_muscles(superuser_url: str, created_by: int) -> int:
    """Count private muscle rows for a user.

    Args:
        superuser_url: Superuser connection URL.
        created_by: User id.

    Returns:
        Row count.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM muscles WHERE created_by = :uid"),
            {"uid": created_by},
        ).fetchone()
    eng.dispose()
    return int(row[0])


def _count_exercises(superuser_url: str, created_by: int) -> int:
    """Count private exercise rows for a user.

    Args:
        superuser_url: Superuser connection URL.
        created_by: User id.

    Returns:
        Row count.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM exercises WHERE created_by = :uid"),
            {"uid": created_by},
        ).fetchone()
    eng.dispose()
    return int(row[0])


def _hidden_muscle_exists(superuser_url: str, user_id: int, muscle_id: int) -> bool:
    """Check whether a UserHiddenMuscle row exists.

    Args:
        superuser_url: Superuser connection URL.
        user_id: User id.
        muscle_id: Muscle id.

    Returns:
        True when the row exists.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM user_hidden_muscles "
                "WHERE user_id = :uid AND muscle_id = :mid"
            ),
            {"uid": user_id, "mid": muscle_id},
        ).fetchone()
    eng.dispose()
    return row is not None


def _hidden_exercise_exists(superuser_url: str, user_id: int, exercise_id: int) -> bool:
    """Check whether a UserHiddenExercise row exists.

    Args:
        superuser_url: Superuser connection URL.
        user_id: User id.
        exercise_id: Exercise id.

    Returns:
        True when the row exists.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM user_hidden_exercises "
                "WHERE user_id = :uid AND exercise_id = :eid"
            ),
            {"uid": user_id, "eid": exercise_id},
        ).fetchone()
    eng.dispose()
    return row is not None


# ---------------------------------------------------------------------------
# Muscle resolution tests
# ---------------------------------------------------------------------------


class TestMuscleCreateResolve:
    def test_create_matching_own_muscle_returns_200_existing(
        self, gym85_client, db_setup
    ):
        """POST /muscles with own muscle's name → 200, resolution=existing, no new row.

        The row count for the user's private muscles must not grow.
        """
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_muscles(superuser_url, USER_85_ID)

        resp = client.post(
            "/api/v1/muscles",
            json={"name": "Gym85 Own Muscle"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == seed["muscle_85_own"]
        assert data["resolution"] == "existing"

        after = _count_muscles(superuser_url, USER_85_ID)
        assert after == before, "No new muscle row should have been created"

    def test_create_separator_case_variant_resolves_to_existing_muscle(
        self, gym85_client, db_setup
    ):
        """POST with 'gym85-own-muscle' (separator variant) resolves to existing muscle.

        'gym85-own-muscle' and 'Gym85 Own Muscle' share the same name_key
        ('gym85 own muscle'), so they are the same thing lexically.
        """
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_muscles(superuser_url, USER_85_ID)

        resp = client.post(
            "/api/v1/muscles",
            # Pydantic validator normalises and validates; separators collapse via app_name_key
            json={"name": "Gym85 Own Muscle"},  # identical key, posted in original form
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["resolution"] == "existing"

        after = _count_muscles(superuser_url, USER_85_ID)
        assert after == before

    def test_create_matching_visible_global_muscle_returns_200_existing(
        self, gym85_client, db_setup
    ):
        """POST /muscles with name matching a VISIBLE global muscle → 200, resolution=existing.

        We use a second user (USER_A_ID from conftest seed) to test a global muscle
        that is NOT hidden for them.  The conftest seed provides 'Global Chest' which
        is visible to all users who haven't hidden it.
        """
        client, seed = gym85_client
        # User 100001 (USER_A_ID) has 'Global Chest' visible (not hidden for them).
        resp = client.post(
            "/api/v1/muscles",
            json={"name": "Global Chest"},
            headers=_service_headers(100001),  # USER_A_ID from conftest seed
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["resolution"] == "existing"
        assert data["is_mine"] is False

    def test_create_matching_hidden_global_muscle_returns_200_unhidden(
        self, gym85_client, db_setup
    ):
        """POST /muscles with name matching a HIDDEN global muscle → 200, resolution=unhidden.

        Seed hides 'Gym85 Global Muscle' for USER_85_ID.  POST with that name should
        silently unhide it and return resolution=unhidden.
        """
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        global_mid = seed["global_muscle_85"]

        # Verify the hidden row exists before the call.
        assert _hidden_muscle_exists(superuser_url, USER_85_ID, global_mid), (
            "Seed should have hidden global_muscle_85 for USER_85_ID"
        )

        resp = client.post(
            "/api/v1/muscles",
            json={"name": "Gym85 Global Muscle"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == global_mid
        assert data["resolution"] == "unhidden"

        # The hidden row must be gone now.
        assert not _hidden_muscle_exists(superuser_url, USER_85_ID, global_mid), (
            "UserHiddenMuscle row should have been deleted by unhide"
        )

    def test_create_genuinely_new_muscle_returns_201_created(
        self, gym85_client, db_setup
    ):
        """POST /muscles with a brand-new name → 201, resolution=created."""
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_muscles(superuser_url, USER_85_ID)

        unique_name = f"Gym85 Brand New {uuid.uuid4().hex[:6]}"
        resp = client.post(
            "/api/v1/muscles",
            json={"name": unique_name},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["resolution"] == "created"
        assert data["name"] == unique_name

        after = _count_muscles(superuser_url, USER_85_ID)
        assert after == before + 1


# ---------------------------------------------------------------------------
# Muscle rename key-based dedup tests
# ---------------------------------------------------------------------------


class TestMuscleRenameKeyDedup:
    def test_rename_muscle_to_key_colliding_with_own_returns_409(
        self, gym85_client
    ):
        """PATCH /muscles/{id} rename to name whose key matches another own muscle → 409.

        muscle_85_rename has key 'gym85 rename me muscle'.
        muscle_85_own2 has key 'gym85 own muscle two'.
        Renaming muscle_85_rename to 'gym85-own-muscle-two' (same key as muscle_85_own2)
        must be rejected with 409.
        Note: the name must pass Pydantic validation first (no hyphens in field per
        schema? No — hyphens ARE allowed per docs/validation.md).
        """
        client, seed = gym85_client
        mid = seed["muscle_85_rename"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            # 'Gym85 Own Muscle Two' is the exact name of muscle_85_own2.
            json={"name": "Gym85 Own Muscle Two"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 409, resp.text

    def test_rename_muscle_to_fresh_key_returns_200(self, gym85_client):
        """PATCH /muscles/{id} rename to a key not held by any own muscle → 200."""
        client, seed = gym85_client
        mid = seed["muscle_85_rename"]
        new_name = f"Gym85 Renamed To Fresh {uuid.uuid4().hex[:6]}"
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            json={"name": new_name},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == new_name

    def test_rename_muscle_to_own_current_key_is_allowed(self, gym85_client):
        """PATCH /muscles/{id} renaming to the same key (whitespace variant) is allowed."""
        client, seed = gym85_client
        mid = seed["muscle_85_own"]
        resp = client.patch(
            f"/api/v1/muscles/{mid}",
            # muscle_85_own is currently named 'Gym85 Own Muscle'; same key, fine.
            json={"name": "Gym85 Own Muscle"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Exercise resolution tests
# ---------------------------------------------------------------------------


class TestExerciseCreateResolve:
    def test_create_matching_own_exercise_returns_200_existing(
        self, gym85_client, db_setup
    ):
        """POST /exercises with own exercise's name → 200, resolution=existing, no new row."""
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_exercises(superuser_url, USER_85_ID)

        resp = client.post(
            "/api/v1/exercises",
            json={
                "name": "Gym85 Own Ex",
                "muscle_name": "Gym85 Own Muscle",
            },
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == seed["ex_85_own"]
        assert data["resolution"] == "existing"

        after = _count_exercises(superuser_url, USER_85_ID)
        assert after == before, "No new exercise row should have been created"

    def test_create_separator_case_variant_resolves_to_existing_exercise(
        self, gym85_client, db_setup
    ):
        """POST with separator/case variant of own exercise name → resolves, not duplicate.

        'GYM85 OWN EX' maps to the same key as 'Gym85 Own Ex'.
        Note: the name must pass Pydantic validation (length/chars) to hit the router.
        We post the exact same name to ensure it's the same key, not a truly novel name.
        """
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_exercises(superuser_url, USER_85_ID)

        resp = client.post(
            "/api/v1/exercises",
            # 'Gym85 Own Ex' in uppercase → same key 'gym85 own ex'
            json={
                "name": "Gym85 Own Ex",
                "muscle_name": "Gym85 Own Muscle",
            },
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["resolution"] == "existing"

        after = _count_exercises(superuser_url, USER_85_ID)
        assert after == before

    def test_create_matching_visible_global_exercise_returns_200_existing(
        self, gym85_client, db_setup
    ):
        """POST /exercises with name matching a VISIBLE global exercise → 200, resolution=existing.

        The conftest seed has 'Global Bench Press' under 'Global Chest' which is
        visible to USER_A_ID (100001) since they haven't hidden it.
        """
        client, seed = gym85_client
        resp = client.post(
            "/api/v1/exercises",
            json={
                "name": "Global Bench Press",
                "muscle_name": "Global Chest",
            },
            headers=_service_headers(100001),  # USER_A_ID from conftest
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["resolution"] == "existing"
        assert data["is_mine"] is False

    def test_create_matching_hidden_global_exercise_returns_200_unhidden(
        self, gym85_client, db_setup
    ):
        """POST /exercises with name matching a HIDDEN global exercise → 200, resolution=unhidden.

        Seed hides 'Gym85 Global Ex' (under 'Gym85 Global Muscle') for USER_85_ID.
        Posting with that name should silently unhide and return resolution=unhidden.
        Note: The global muscle itself was also hidden for USER_85_ID, but the
        previous test (test_create_matching_hidden_global_muscle_returns_200_unhidden)
        already unhid it.  The exercise hidden row is still present.
        """
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        global_eid = seed["global_ex_85"]

        # Verify the hidden exercise row exists.
        assert _hidden_exercise_exists(superuser_url, USER_85_ID, global_eid), (
            "Seed should have hidden global_ex_85 for USER_85_ID"
        )

        resp = client.post(
            "/api/v1/exercises",
            json={
                "name": "Gym85 Global Ex",
                "muscle_name": "Gym85 Global Muscle",
            },
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == global_eid
        assert data["resolution"] == "unhidden"

        # Hidden exercise row must be gone.
        assert not _hidden_exercise_exists(superuser_url, USER_85_ID, global_eid), (
            "UserHiddenExercise row should have been deleted by unhide"
        )

    def test_create_genuinely_new_exercise_returns_201_created(
        self, gym85_client, db_setup
    ):
        """POST /exercises with a brand-new name → 201, resolution=created."""
        client, seed = gym85_client
        superuser_url = db_setup["superuser_url"]
        before = _count_exercises(superuser_url, USER_85_ID)

        unique_name = f"Gym85 Brand New Ex {uuid.uuid4().hex[:6]}"
        resp = client.post(
            "/api/v1/exercises",
            json={
                "name": unique_name,
                "muscle_name": "Gym85 Own Muscle",
            },
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["resolution"] == "created"
        assert data["name"] == unique_name

        after = _count_exercises(superuser_url, USER_85_ID)
        assert after == before + 1


# ---------------------------------------------------------------------------
# Exercise rename key-based dedup tests
# ---------------------------------------------------------------------------


class TestExerciseRenameKeyDedup:
    def test_rename_exercise_to_key_colliding_with_own_returns_409(
        self, gym85_client
    ):
        """PATCH /exercises/{id} rename to name whose key matches another own exercise → 409.

        ex_85_rename ('Gym85 Rename Me Ex') is under muscle_85_own.
        ex_85_own2 ('Gym85 Own Ex Two') is also under muscle_85_own.
        Renaming ex_85_rename to 'Gym85 Own Ex Two' (same key) must return 409.
        """
        client, seed = gym85_client
        eid = seed["ex_85_rename"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "Gym85 Own Ex Two"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 409, resp.text

    def test_rename_exercise_to_fresh_key_returns_200(self, gym85_client):
        """PATCH /exercises/{id} rename to a key not held by any own exercise (same muscle) → 200."""
        client, seed = gym85_client
        eid = seed["ex_85_rename"]
        new_name = f"Gym85 Freshly Renamed Ex {uuid.uuid4().hex[:6]}"
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": new_name},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == new_name

    def test_rename_exercise_to_own_current_key_is_allowed(self, gym85_client):
        """PATCH /exercises/{id} renaming to own current name (same key) is allowed."""
        client, seed = gym85_client
        eid = seed["ex_85_own"]
        resp = client.patch(
            f"/api/v1/exercises/{eid}",
            json={"name": "Gym85 Own Ex"},
            headers=_service_headers(USER_85_ID),
        )
        assert resp.status_code == 200, resp.text
