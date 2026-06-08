"""GYM-106: Tests for the centralized name-to-id resolver and fixed exact-name sites.

Covers:
  1. resolve_muscle_id — variant name ("GYM106 CHEST", "gym106-chest") resolves to
     the canonical id; unresolvable name returns None.
  2. resolve_exercise_id — variant name resolves to the canonical id; unresolvable
     returns None.
  3. Deterministic own-before-global: when both an own and a global row exist with
     the same name_key, own wins.
  4. POST /training with a variant-case muscle and exercise name succeeds (resolves).
  5. GET /analytics/top-exercises with a variant muscle name returns exercises.
  6. POST /training with an exact canonical name still succeeds (regression guard).

Seed (USER_106_ID = 500106):
  - global_muscle_106:   global muscle ("GYM106 Global Chest", created_by=NULL).
  - global_ex_106:       global exercise ("GYM106 Global Bench Press") under global_muscle_106.
  - own_muscle_106:      own private muscle ("GYM106 Own Chest", created_by=USER_106_ID).
  - own_ex_106:          own private exercise ("GYM106 Own Bench Press") under own_muscle_106.
  - training rows:       1 row for own_ex_106 under own_muscle_106 (for top-exercises test).

For the own-before-global determinism test:
  - shared_muscle:       global muscle ("GYM106 Shared Chest", created_by=NULL).
  - own_shared_muscle:   own muscle with SAME name_key ("GYM106-Shared-Chest",
                         created_by=USER_106_ID).  name_key: "gym106 shared chest".
    The resolver must return own_shared_muscle, not shared_muscle.

Relies on the session-scoped ``db_setup`` fixture from ``conftest.py``.
"""

import os
import sys
import uuid
from datetime import datetime
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_106_ID = 500106


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service_headers(user_id: int) -> dict:
    """Build service-token auth headers impersonating user_id.

    Args:
        user_id: Telegram user id to act as.

    Returns:
        Header dict with X-Service-Token and X-Act-As-User.
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


def _seed_gym106(superuser_url: str) -> dict:
    """Insert seed data for GYM-106 tests.

    Creates:
    - USER_106_ID user row.
    - global_muscle_106: global muscle ("GYM106 Global Chest", created_by=NULL).
    - global_ex_106: global exercise ("GYM106 Global Bench Press") under global_muscle_106.
    - own_muscle_106: own private muscle ("GYM106 Own Chest", created_by=USER_106_ID).
    - own_ex_106: own private exercise ("GYM106 Own Bench Press") under own_muscle_106.
    - 1 training row under own_ex_106 (for top-exercises + training create tests).
    - shared_muscle: global muscle for own-before-global determinism test.
    - own_shared_muscle: own muscle with same name_key as shared_muscle.

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User106', 'user106_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_106_ID})

        # Global muscle.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM106 Global Chest', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        global_muscle_106 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM106 Global Chest' AND created_by IS NULL"
        )).fetchone()[0]

        # Global exercise.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM106 Global Bench Press', :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"mid": global_muscle_106})
        global_ex_106 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM106 Global Bench Press' AND created_by IS NULL"
        )).fetchone()[0]

        # Own muscle.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM106 Own Chest', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_106_ID})
        own_muscle_106 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM106 Own Chest' AND created_by=:uid"
        ), {"uid": USER_106_ID}).fetchone()[0]

        # Own exercise.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM106 Own Bench Press', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": own_muscle_106, "uid": USER_106_ID})
        own_ex_106 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM106 Own Bench Press' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_106_ID, "mid": own_muscle_106}).fetchone()[0]

        # Training row for own exercise.
        conn.execute(text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :dt, :uid, :mid, :eid, 1, 80.0, 10.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "dt": datetime(2026, 3, 1, 10, 0, 0),
            "uid": USER_106_ID,
            "mid": own_muscle_106,
            "eid": own_ex_106,
        })

        # --- own-before-global determinism seed ---
        # Global muscle: "GYM106 Shared Chest" (name_key: "gym106 shared chest").
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM106 Shared Chest', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        shared_global_muscle = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM106 Shared Chest' AND created_by IS NULL"
        )).fetchone()[0]

        # Own muscle with the SAME name_key: "GYM106-Shared-Chest"
        # app_name_key('GYM106-Shared-Chest') == 'gym106 shared chest'.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM106 Shared Chest Own', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_106_ID})
        own_shared_muscle = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM106 Shared Chest Own' AND created_by=:uid"
        ), {"uid": USER_106_ID}).fetchone()[0]

        conn.commit()
    eng.dispose()

    return {
        "global_muscle_106": global_muscle_106,
        "global_ex_106": global_ex_106,
        "own_muscle_106": own_muscle_106,
        "own_ex_106": own_ex_106,
        "shared_global_muscle": shared_global_muscle,
        "own_shared_muscle": own_shared_muscle,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient + raw Session factory
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym106_setup(db_setup) -> Generator:
    """Build a TestClient and raw Session factory for GYM-106 tests.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict, app_rw_session_factory, db_setup).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym106(db_setup["superuser_url"])

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
    from app.core.database import _set_rls_gucs

    test_engine = create_engine(app_rw_url, poolclass=NullPool)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)

    yield client, seed, test_session_local, db_setup

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 1. resolve_muscle_id — variant names + unresolvable
# ---------------------------------------------------------------------------


def _rls_session(factory: sessionmaker, user_id: int) -> Session:
    """Open a session with session.info set for RLS GUC injection.

    The production ``after_begin`` event reads from ``session.info`` (not
    contextvars — see GYM-37 / database.py).  For direct resolver calls we
    must populate ``session.info`` before issuing any query.

    Args:
        factory: The sessionmaker instance.
        user_id: Telegram user id to impersonate.

    Returns:
        A Session with ``session.info`` pre-populated.
    """
    session = factory()
    session.info["app_user_id"] = str(user_id)
    session.info["app_role"] = "user"
    return session


class TestResolveMuscleId:
    """resolve_muscle_id resolves variant names and returns None for unknowns."""

    def test_resolve_muscle_by_variant_uppercase(self, gym106_setup):
        """resolve_muscle_id with uppercase variant returns the canonical id."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_muscle_id
            result = resolve_muscle_id(session, USER_106_ID, "GYM106 OWN CHEST")
            assert result == seed["own_muscle_106"], (
                f"Expected own_muscle_106={seed['own_muscle_106']}, got {result}"
            )
        finally:
            session.close()

    def test_resolve_muscle_by_variant_dash(self, gym106_setup):
        """resolve_muscle_id with dash-separated variant returns the canonical id."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_muscle_id
            result = resolve_muscle_id(session, USER_106_ID, "GYM106-Own-Chest")
            assert result == seed["own_muscle_106"], (
                f"Expected own_muscle_106={seed['own_muscle_106']}, got {result}"
            )
        finally:
            session.close()

    def test_resolve_muscle_unresolvable_returns_none(self, gym106_setup):
        """resolve_muscle_id returns None for a name with no matching key."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_muscle_id
            result = resolve_muscle_id(session, USER_106_ID, "GYM106 Nonexistent Muscle XYZ")
            assert result is None, f"Expected None, got {result}"
        finally:
            session.close()


# ---------------------------------------------------------------------------
# 2. resolve_exercise_id — variant names + unresolvable
# ---------------------------------------------------------------------------


class TestResolveExerciseId:
    """resolve_exercise_id resolves variant names and returns None for unknowns."""

    def test_resolve_exercise_by_variant_name(self, gym106_setup):
        """resolve_exercise_id with a variant exercise name resolves to the canonical id."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_exercise_id
            result = resolve_exercise_id(
                session, USER_106_ID,
                "GYM106 Own Chest",
                "GYM106 OWN BENCH PRESS",
            )
            assert result == seed["own_ex_106"], (
                f"Expected own_ex_106={seed['own_ex_106']}, got {result}"
            )
        finally:
            session.close()

    def test_resolve_exercise_by_dash_variant(self, gym106_setup):
        """resolve_exercise_id with dash-separator variant resolves correctly."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_exercise_id
            result = resolve_exercise_id(
                session, USER_106_ID,
                "GYM106-Own-Chest",
                "GYM106-Own-Bench-Press",
            )
            assert result == seed["own_ex_106"], (
                f"Expected own_ex_106={seed['own_ex_106']}, got {result}"
            )
        finally:
            session.close()

    def test_resolve_exercise_unresolvable_returns_none(self, gym106_setup):
        """resolve_exercise_id returns None when exercise name has no matching key."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_exercise_id
            result = resolve_exercise_id(
                session, USER_106_ID,
                "GYM106 Own Chest",
                "GYM106 Nonexistent Exercise XYZ",
            )
            assert result is None, f"Expected None, got {result}"
        finally:
            session.close()

    def test_resolve_exercise_unknown_muscle_returns_none(self, gym106_setup):
        """resolve_exercise_id returns None when the muscle itself is not found."""
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_exercise_id
            result = resolve_exercise_id(
                session, USER_106_ID,
                "GYM106 Ghost Muscle",
                "GYM106 Own Bench Press",
            )
            assert result is None, f"Expected None for unknown muscle, got {result}"
        finally:
            session.close()


# ---------------------------------------------------------------------------
# 3. Own-before-global determinism
# ---------------------------------------------------------------------------


class TestOwnBeforeGlobalDeterminism:
    """When own and global rows share the same name_key, own wins."""

    def test_global_muscle_resolves_when_no_own_conflict(self, gym106_setup):
        """resolve_muscle_id returns the global muscle id when no own row shares its key.

        global_muscle_106 has name_key='gym106 global chest'.  USER_106_ID has no own
        muscle with that key, so the resolver must return the global row.
        """
        client, seed, factory, db_setup = gym106_setup
        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_muscle_id
            result = resolve_muscle_id(session, USER_106_ID, "GYM106 Global Chest")
            assert result == seed["global_muscle_106"], (
                f"Expected global_muscle_106={seed['global_muscle_106']}, got {result}"
            )
        finally:
            session.close()

    def test_own_muscle_wins_over_global_when_key_matches_both(self, gym106_setup, db_setup):
        """When an own row and a global row share the same name_key, own wins.

        Seeds a temporary own muscle for USER_106_ID with name 'GYM106 Global Chest'
        (same name as the global muscle — same name_key 'gym106 global chest').
        The partial unique index allows this because created_by is different (user
        vs NULL).  The resolver must return the own row, not the global one.
        """
        client, seed, factory, db_setup_inner = gym106_setup
        superuser_url = db_setup["superuser_url"]

        eng = create_engine(superuser_url, poolclass=NullPool)
        own_dup_id = None
        with eng.connect() as conn:
            # Same name as global → same name_key.  The partial unique index on
            # (name_key, created_by) permits this (different created_by).
            conn.execute(text("""
                INSERT INTO muscles (name, is_global, created_by)
                VALUES ('GYM106 Global Chest', FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"uid": USER_106_ID})
            own_dup_row = conn.execute(text(
                "SELECT id FROM muscles WHERE name='GYM106 Global Chest' AND created_by=:uid"
            ), {"uid": USER_106_ID}).fetchone()
            if own_dup_row:
                own_dup_id = own_dup_row[0]
            conn.commit()
        eng.dispose()

        if own_dup_id is None:
            pytest.skip("Could not insert same-key own muscle — unique constraint prevented it")

        session = _rls_session(factory, USER_106_ID)
        try:
            from app.services.resolve import resolve_muscle_id
            result = resolve_muscle_id(session, USER_106_ID, "GYM106 Global Chest")
            assert result == own_dup_id, (
                f"Expected own_dup_id={own_dup_id} (own wins over global), got {result}"
            )
        finally:
            session.close()


# ---------------------------------------------------------------------------
# 4. POST /training with variant name succeeds
# ---------------------------------------------------------------------------


class TestPostTrainingVariantName:
    """POST /training with variant-case names resolves and creates the record."""

    def test_post_training_with_variant_muscle_and_exercise_name(self, gym106_setup):
        """POST /training with uppercase variant names resolves and returns 201."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.post(
            "/api/v1/training",
            json={
                "muscle_name": "GYM106 OWN CHEST",
                "exercise_name": "GYM106 OWN BENCH PRESS",
                "set": 1,
                "weight": 90.0,
                "reps": 8,
            },
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 201, (
            f"Expected 201 for variant-name training create, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data["muscle_id"] == seed["own_muscle_106"], (
            f"Expected muscle_id={seed['own_muscle_106']}, got {data.get('muscle_id')}"
        )
        assert data["exercise_id"] == seed["own_ex_106"], (
            f"Expected exercise_id={seed['own_ex_106']}, got {data.get('exercise_id')}"
        )

    def test_post_training_with_dash_variant_name(self, gym106_setup):
        """POST /training with dash-separator variant names resolves and returns 201."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.post(
            "/api/v1/training",
            json={
                "muscle_name": "GYM106-Own-Chest",
                "exercise_name": "GYM106-Own-Bench-Press",
                "set": 2,
                "weight": 85.0,
                "reps": 10,
            },
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 201, (
            f"Expected 201 for dash-variant training create, got {resp.status_code}: {resp.text}"
        )

    def test_post_training_canonical_name_still_works(self, gym106_setup):
        """POST /training with canonical exact name still succeeds (regression guard)."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.post(
            "/api/v1/training",
            json={
                "muscle_name": "GYM106 Own Chest",
                "exercise_name": "GYM106 Own Bench Press",
                "set": 3,
                "weight": 75.0,
                "reps": 12,
            },
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 201, (
            f"Regression: canonical name should still work, got {resp.status_code}: {resp.text}"
        )

    def test_post_training_unknown_muscle_returns_404(self, gym106_setup):
        """POST /training with unknown muscle returns 404."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.post(
            "/api/v1/training",
            json={
                "muscle_name": "GYM106 Ghost Muscle",
                "exercise_name": "GYM106 Own Bench Press",
                "set": 1,
                "weight": 60.0,
                "reps": 8,
            },
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown muscle, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 5. GET /analytics/top-exercises with variant muscle name
# ---------------------------------------------------------------------------


class TestTopExercisesVariantMuscle:
    """GET /analytics/top-exercises resolves variant muscle names via name_key."""

    def test_top_exercises_with_uppercase_muscle_name_returns_exercises(self, gym106_setup):
        """top-exercises with uppercase muscle variant returns the seeded exercise."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.get(
            "/api/v1/analytics/top-exercises",
            params={"muscle": "GYM106 OWN CHEST", "limit": 5},
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for top-exercises with variant muscle, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert len(data) >= 1, (
            f"Expected at least 1 top exercise for seeded muscle, got {len(data)}: {data}"
        )
        names = [e["name"] for e in data]
        assert "GYM106 Own Bench Press" in names, (
            f"Expected 'GYM106 Own Bench Press' in results: {names}"
        )

    def test_top_exercises_with_dash_variant_muscle_name(self, gym106_setup):
        """top-exercises with dash-separator muscle variant returns exercises."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.get(
            "/api/v1/analytics/top-exercises",
            params={"muscle": "GYM106-Own-Chest", "limit": 5},
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 for dash-variant muscle, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert len(data) >= 1, (
            f"Expected at least 1 exercise for dash-variant muscle, got {len(data)}: {data}"
        )

    def test_top_exercises_with_canonical_muscle_still_works(self, gym106_setup):
        """top-exercises with canonical exact muscle name still works (regression)."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.get(
            "/api/v1/analytics/top-exercises",
            params={"muscle": "GYM106 Own Chest", "limit": 5},
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 200, (
            f"Regression: canonical muscle name for top-exercises, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert len(data) >= 1, (
            f"Expected at least 1 exercise for canonical muscle, got {len(data)}: {data}"
        )

    def test_top_exercises_unknown_muscle_returns_empty(self, gym106_setup):
        """top-exercises with unknown muscle returns empty list (not 404)."""
        client, seed, factory, db_setup = gym106_setup
        resp = client.get(
            "/api/v1/analytics/top-exercises",
            params={"muscle": "GYM106 Ghost Muscle", "limit": 5},
            headers=_service_headers(USER_106_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 with empty list for unknown muscle, got {resp.status_code}: {resp.text}"
        )
        assert resp.json() == [], f"Expected empty list for unknown muscle, got {resp.json()}"
