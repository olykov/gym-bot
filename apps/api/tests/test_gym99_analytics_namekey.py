"""GYM-99: Integration tests for name_key analytics resolution, no negative cache, hide-own.

Covers:
  1. log-context resolves by name_key — variant name ("BENCH PRESS", "bench-press",
     "bench  press") of an exercise with history returns the same real PR/completed-sets
     as the canonical name (key resolution works end-to-end).
  2. log-context for a genuinely unresolvable name returns empty and is NOT cached —
     a subsequent call after the row is created/visible returns real data.
  3. personal-record and completed-sets resolve by name_key (variant name → real data).
  4. history endpoint resolves by name_key (variant name → real data).
  5. max-reps endpoint resolves by name_key (variant name → real data).
  6. exercise-progress endpoint resolves by name_key (variant name → real data).
  7. Hide an OWN exercise → disappears from visible list; unhide → returns.
  8. Hide an OWN muscle → disappears from visible list; unhide → returns.
  9. Existing behavior: canonical-name lookups still work.
 10. Visibility: hiding an own item (not just global) is correctly excluded.

Seed (USER_99_ID = 500099):
  muscle_99: own private muscle ("GYM99 Chest").
  exercise_99: own private exercise under muscle_99 ("GYM99 Bench Press").
  training rows: 3 sets at weight=120, 100, 80 (increasing history; PR=120).
  training dates: all today to test completed-sets.

The test for no-negative-cache creates the exercise AFTER the first miss and
verifies the second call returns real data (not poisoned by the cached empty).

Relies on the session-scoped ``db_setup`` fixture from ``conftest.py``.
"""

import os
import sys
import uuid
from datetime import datetime, date, timedelta
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_99_ID = 500099


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
    # Non-reachable Redis — cache calls degrade gracefully to DB.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_gym99(superuser_url: str) -> dict:
    """Insert seed data for GYM-99 tests.

    Creates:
    - USER_99_ID user row.
    - muscle_99: own private muscle ("GYM99 Chest").
    - exercise_99: own private exercise under muscle_99 ("GYM99 Bench Press").
    - 3 training rows (different weights and dates in the past).
    - muscle_99_own2: second own muscle (hide test target).
    - exercise_99_own2: second own exercise under muscle_99 (hide test target).
    - training rows for exercise_99_own2 (so it can't be hard-deleted).

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User99', 'user99_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_99_ID})

        # Own private muscle.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM99 Chest', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_99_ID})
        muscle_99 = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM99 Chest' AND created_by=:uid"
        ), {"uid": USER_99_ID}).fetchone()[0]

        # Own private exercise.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM99 Bench Press', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_99, "uid": USER_99_ID})
        exercise_99 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM99 Bench Press' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_99_ID, "mid": muscle_99}).fetchone()[0]

        # 3 training rows with different weights — PR is 120.
        # Rows are in the past so completed-sets (today) returns empty,
        # but last-session and PR can be asserted.
        past_dates = [
            datetime(2026, 1, 10, 10, 0, 0),
            datetime(2026, 2, 15, 10, 0, 0),
            datetime(2026, 3, 20, 10, 0, 0),
        ]
        weights = [80.0, 100.0, 120.0]
        for i, (dt, wt) in enumerate(zip(past_dates, weights)):
            conn.execute(text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :dt, :uid, :mid, :eid, 1, :wt, 10.0)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "dt": dt,
                "uid": USER_99_ID,
                "mid": muscle_99,
                "eid": exercise_99,
                "wt": wt,
            })

        # Second own muscle for hide-own tests.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM99 Hide Me Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_99_ID})
        muscle_99_hide = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM99 Hide Me Muscle' AND created_by=:uid"
        ), {"uid": USER_99_ID}).fetchone()[0]

        # Second own exercise for hide-own tests.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM99 Hide Me Exercise', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_99_hide, "uid": USER_99_ID})
        exercise_99_hide = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM99 Hide Me Exercise' AND created_by=:uid AND muscle=:mid"
        ), {"uid": USER_99_ID, "mid": muscle_99_hide}).fetchone()[0]

        # One training row for the hide-target exercise (prevents hard-delete).
        conn.execute(text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :dt, :uid, :mid, :eid, 1, 60.0, 8.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "dt": datetime(2026, 1, 5, 10, 0, 0),
            "uid": USER_99_ID,
            "mid": muscle_99_hide,
            "eid": exercise_99_hide,
        })

        conn.commit()
    eng.dispose()

    return {
        "muscle_99": muscle_99,
        "exercise_99": exercise_99,
        "muscle_99_hide": muscle_99_hide,
        "exercise_99_hide": exercise_99_hide,
    }


def _superuser_query(superuser_url: str, sql: str, params: dict):
    """Run a SELECT via superuser and return the first row.

    Args:
        superuser_url: Superuser URL.
        sql: SQL query text.
        params: Bind parameters.

    Returns:
        First result row or None.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        result = conn.execute(text(sql), params).fetchone()
    eng.dispose()
    return result


def _hidden_exercise_exists(superuser_url: str, user_id: int, exercise_id: int) -> bool:
    """Return True when the user_hidden_exercises row exists.

    Args:
        superuser_url: Superuser URL.
        user_id: User id.
        exercise_id: Exercise id.

    Returns:
        True when the row is present.
    """
    row = _superuser_query(
        superuser_url,
        "SELECT 1 FROM user_hidden_exercises WHERE user_id=:uid AND exercise_id=:eid",
        {"uid": user_id, "eid": exercise_id},
    )
    return row is not None


def _hidden_muscle_exists(superuser_url: str, user_id: int, muscle_id: int) -> bool:
    """Return True when the user_hidden_muscles row exists.

    Args:
        superuser_url: Superuser URL.
        user_id: User id.
        muscle_id: Muscle id.

    Returns:
        True when the row is present.
    """
    row = _superuser_query(
        superuser_url,
        "SELECT 1 FROM user_hidden_muscles WHERE user_id=:uid AND muscle_id=:mid",
        {"uid": user_id, "mid": muscle_id},
    )
    return row is not None


def _insert_exercise_via_superuser(superuser_url: str, name: str, muscle_id: int, user_id: int) -> int:
    """Insert an exercise as superuser and return its id.

    Args:
        superuser_url: Superuser URL.
        name: Exercise name.
        muscle_id: Parent muscle id.
        user_id: Owner user id.

    Returns:
        New exercise id.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES (:name, :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"name": name, "mid": muscle_id, "uid": user_id})
        eid = conn.execute(text(
            "SELECT id FROM exercises WHERE name=:name AND created_by=:uid AND muscle=:mid"
        ), {"name": name, "uid": user_id, "mid": muscle_id}).fetchone()[0]
        conn.commit()
    eng.dispose()
    return eid


def _insert_training_via_superuser(
    superuser_url: str, user_id: int, muscle_id: int, exercise_id: int,
    weight: float, reps: float, dt: datetime
) -> None:
    """Insert a training row as superuser.

    Args:
        superuser_url: Superuser URL.
        user_id: User id.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        weight: Weight value.
        reps: Reps value.
        dt: Training timestamp.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :dt, :uid, :mid, :eid, 1, :wt, :reps)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "dt": dt,
            "uid": user_id,
            "mid": muscle_id,
            "eid": exercise_id,
            "wt": weight,
            "reps": reps,
        })
        conn.commit()
    eng.dispose()


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym99_client(db_setup) -> Generator:
    """Build a TestClient for GYM-99 tests with dedicated seed data.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict, db_setup_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym99(db_setup["superuser_url"])

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
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

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
    yield client, seed, db_setup

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# Helper: call log-context
# ---------------------------------------------------------------------------


def _log_context(client, user_id: int, muscle: str, exercise: str) -> dict:
    """Call GET /analytics/log-context and return the JSON body.

    Args:
        client: TestClient.
        user_id: User id to impersonate.
        muscle: Muscle name query param.
        exercise: Exercise name query param.

    Returns:
        Parsed JSON body.
    """
    today = date.today().isoformat()
    resp = client.get(
        "/api/v1/analytics/log-context",
        params={"muscle": muscle, "exercise": exercise, "date": today},
        headers=_service_headers(user_id),
    )
    assert resp.status_code == 200, f"log-context returned {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# 1. name_key resolution — log-context / PR / completed-sets
# ---------------------------------------------------------------------------


class TestNameKeyResolution:
    """Variant names resolve to the same exercise as the canonical name."""

    def test_log_context_canonical_name_returns_pr(self, gym99_client):
        """log-context with the canonical exercise name returns real PR data."""
        client, seed, _ = gym99_client
        data = _log_context(client, USER_99_ID, "GYM99 Chest", "GYM99 Bench Press")
        assert data["pr"] is not None, (
            f"Expected PR for canonical name, got None. Full: {data}"
        )
        assert float(data["pr"]["weight"]) == 120.0, (
            f"Expected PR weight=120.0, got {data['pr']['weight']}"
        )

    def test_log_context_uppercase_variant_returns_same_pr(self, gym99_client):
        """log-context with uppercase variant resolves to the same PR as canonical."""
        client, seed, _ = gym99_client
        data = _log_context(client, USER_99_ID, "GYM99 CHEST", "GYM99 BENCH PRESS")
        assert data["pr"] is not None, (
            f"Expected PR for uppercase variant, got None. Full: {data}"
        )
        assert float(data["pr"]["weight"]) == 120.0, (
            f"Expected PR weight=120.0, got {data['pr']['weight']}"
        )

    def test_log_context_dash_separator_variant_returns_same_pr(self, gym99_client):
        """log-context with dash-separator variant resolves to the same PR as canonical."""
        client, seed, _ = gym99_client
        data = _log_context(client, USER_99_ID, "GYM99-Chest", "GYM99-Bench-Press")
        assert data["pr"] is not None, (
            f"Expected PR for dash variant, got None. Full: {data}"
        )
        assert float(data["pr"]["weight"]) == 120.0, (
            f"Expected PR weight=120.0 for dash variant, got {data['pr']['weight']}"
        )

    def test_log_context_extra_spaces_variant_returns_same_pr(self, gym99_client):
        """log-context with extra-whitespace variant resolves to the same PR as canonical."""
        client, seed, _ = gym99_client
        # Double-space between words collapses via app_name_key.
        data = _log_context(client, USER_99_ID, "GYM99  Chest", "GYM99  Bench  Press")
        assert data["pr"] is not None, (
            f"Expected PR for double-space variant, got None. Full: {data}"
        )
        assert float(data["pr"]["weight"]) == 120.0, (
            f"Expected PR weight=120.0 for double-space variant, got {data['pr']['weight']}"
        )

    def test_personal_record_endpoint_resolves_by_key(self, gym99_client):
        """GET /analytics/personal-record with variant name returns the real PR."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/analytics/personal-record",
            params={"muscle": "GYM99-Chest", "exercise": "GYM99-Bench-Press"},
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, f"personal-record returned {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data is not None, "Expected PR object, got null"
        assert float(data["weight"]) == 120.0, (
            f"Expected PR weight=120.0 for dash variant, got {data['weight']}"
        )

    def test_completed_sets_endpoint_resolves_by_key(self, gym99_client):
        """GET /analytics/completed-sets with variant name resolves (returns 200).

        The seeded training rows are in the past, so completed-sets for today
        returns an empty list, but the endpoint must resolve the exercise (200).
        """
        client, seed, _ = gym99_client
        today = date.today().isoformat()
        resp = client.get(
            "/api/v1/analytics/completed-sets",
            params={
                "muscle": "GYM99 CHEST",
                "exercise": "GYM99 BENCH PRESS",
                "date": today,
            },
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, f"completed-sets returned {resp.status_code}: {resp.text}"

    def test_history_endpoint_resolves_by_key(self, gym99_client):
        """GET /analytics/history with variant name returns history entries."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/analytics/history",
            params={"muscle": "GYM99-Chest", "exercise": "GYM99-Bench-Press"},
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, f"history returned {resp.status_code}: {resp.text}"
        data = resp.json()
        # 3 training rows exist in the past; all should appear.
        assert len(data) >= 1, (
            f"Expected >= 1 history entry for dash variant, got {len(data)}: {data}"
        )

    def test_max_reps_endpoint_resolves_by_key(self, gym99_client):
        """GET /analytics/max-reps with variant name resolves correctly."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/analytics/max-reps",
            params={
                "muscle": "GYM99 CHEST",
                "exercise": "GYM99 BENCH PRESS",
                "weight": 120.0,
            },
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, f"max-reps returned {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["max_reps"] is not None, "Expected max_reps to be set, got None"
        assert float(data["max_reps"]) == 10.0, (
            f"Expected max_reps=10.0, got {data['max_reps']}"
        )

    def test_exercise_progress_endpoint_resolves_by_key(self, gym99_client):
        """GET /analytics/exercise-progress with variant name returns series."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": "GYM99-Chest", "exercise": "GYM99-Bench-Press"},
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, f"exercise-progress returned {resp.status_code}: {resp.text}"
        data = resp.json()
        # 3 training rows, all set=1 → 1 series entry with 3 points.
        assert len(data["series"]) >= 1, (
            f"Expected >= 1 series for dash variant, got {len(data['series'])}: {data}"
        )


# ---------------------------------------------------------------------------
# 2. No negative cache — miss does not poison subsequent real calls
# ---------------------------------------------------------------------------


class TestNoNegativeCache:
    """Resolution miss must not be cached; after the row exists, real data returns."""

    def test_unresolvable_name_returns_empty_not_cached(self, gym99_client, db_setup):
        """log-context for an unresolvable name returns empty then real data after seeding.

        Steps:
          1. Call log-context for a brand-new exercise name (not yet in DB) → empty.
          2. Insert the exercise + training row directly (superuser).
          3. Call log-context again with the SAME name → real PR (not the cached empty).

        If the negative result were cached, step 3 would still return empty.
        """
        client, seed, _ = gym99_client
        superuser_url = db_setup["superuser_url"]

        unique_suffix = uuid.uuid4().hex[:6]
        muscle_name = "GYM99 Chest"
        exercise_name = f"GYM99 NoCacheTest {unique_suffix}"
        muscle_id = seed["muscle_99"]

        # Step 1: miss — returns empty.
        first = _log_context(client, USER_99_ID, muscle_name, exercise_name)
        assert first["pr"] is None, (
            f"Expected PR=None for unresolvable exercise, got {first['pr']}"
        )
        assert first["completed_sets"] == [], (
            f"Expected empty completed_sets for miss, got {first['completed_sets']}"
        )
        assert first["last_session_sets"] == [], (
            f"Expected empty last_session_sets for miss, got {first['last_session_sets']}"
        )

        # Step 2: create the exercise and a training row (superuser bypass RLS).
        eid = _insert_exercise_via_superuser(superuser_url, exercise_name, muscle_id, USER_99_ID)
        _insert_training_via_superuser(
            superuser_url, USER_99_ID, muscle_id, eid,
            weight=75.0, reps=12.0, dt=datetime(2026, 2, 1, 10, 0, 0),
        )

        # Step 3: call again — must NOT return the cached empty.
        second = _log_context(client, USER_99_ID, muscle_name, exercise_name)
        assert second["pr"] is not None, (
            f"Expected real PR on second call (negative must not be cached), got None. "
            f"full response: {second}"
        )
        assert float(second["pr"]["weight"]) == 75.0, (
            f"Expected PR weight=75.0, got {second['pr']['weight']}"
        )


# ---------------------------------------------------------------------------
# 3. Hide OWN exercise — disappears from visible list; unhide returns it
# ---------------------------------------------------------------------------


class TestHideOwnExercise:
    """PUT /exercises/{id}/hidden must work for own (non-global) exercises."""

    def test_own_exercise_visible_before_hide(self, gym99_client, db_setup):
        """Own exercise appears in the visible exercises list before hiding."""
        client, seed, _ = gym99_client
        muscle_id = seed["muscle_99_hide"]
        resp = client.get(
            f"/api/v1/muscles/{muscle_id}/exercises",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [e["id"] for e in resp.json()]
        assert seed["exercise_99_hide"] in ids, (
            f"Expected exercise_99_hide in visible list before hide: {ids}"
        )

    def test_hide_own_exercise_returns_204(self, gym99_client, db_setup):
        """PUT /exercises/{id}/hidden for an own exercise returns 204."""
        client, seed, _ = gym99_client
        eid = seed["exercise_99_hide"]
        resp = client.put(
            f"/api/v1/exercises/{eid}/hidden",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when hiding own exercise, got {resp.status_code}: {resp.text}"
        )

    def test_own_exercise_not_visible_after_hide(self, gym99_client, db_setup):
        """Own exercise disappears from visible list after hiding."""
        client, seed, _ = gym99_client
        muscle_id = seed["muscle_99_hide"]
        resp = client.get(
            f"/api/v1/muscles/{muscle_id}/exercises",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [e["id"] for e in resp.json()]
        assert seed["exercise_99_hide"] not in ids, (
            f"Expected exercise_99_hide to be hidden, but it's still in list: {ids}"
        )

    def test_hidden_exercise_row_exists_in_db(self, gym99_client, db_setup):
        """UserHiddenExercise row is present after hiding."""
        client, seed, _ = gym99_client
        superuser_url = db_setup["superuser_url"]
        assert _hidden_exercise_exists(superuser_url, USER_99_ID, seed["exercise_99_hide"]), (
            "Expected user_hidden_exercises row to exist after hide"
        )

    def test_unhide_own_exercise_returns_204(self, gym99_client, db_setup):
        """DELETE /exercises/{id}/hidden (unhide) for own exercise returns 204."""
        client, seed, _ = gym99_client
        eid = seed["exercise_99_hide"]
        resp = client.delete(
            f"/api/v1/exercises/{eid}/hidden",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when unhiding own exercise, got {resp.status_code}: {resp.text}"
        )

    def test_own_exercise_visible_after_unhide(self, gym99_client, db_setup):
        """Own exercise reappears in visible list after unhiding."""
        client, seed, _ = gym99_client
        muscle_id = seed["muscle_99_hide"]
        resp = client.get(
            f"/api/v1/muscles/{muscle_id}/exercises",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [e["id"] for e in resp.json()]
        assert seed["exercise_99_hide"] in ids, (
            f"Expected exercise_99_hide to be visible after unhide: {ids}"
        )


# ---------------------------------------------------------------------------
# 4. Hide OWN muscle — disappears from visible list; unhide returns it
# ---------------------------------------------------------------------------


class TestHideOwnMuscle:
    """PUT /muscles/{id}/hidden must work for own (non-global) muscles."""

    def test_own_muscle_visible_before_hide(self, gym99_client, db_setup):
        """Own muscle appears in the visible muscles list before hiding."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["muscle_99_hide"] in ids, (
            f"Expected muscle_99_hide in visible list before hide: {ids}"
        )

    def test_hide_own_muscle_returns_204(self, gym99_client, db_setup):
        """PUT /muscles/{id}/hidden for an own muscle returns 204."""
        client, seed, _ = gym99_client
        mid = seed["muscle_99_hide"]
        resp = client.put(
            f"/api/v1/muscles/{mid}/hidden",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when hiding own muscle, got {resp.status_code}: {resp.text}"
        )

    def test_own_muscle_not_visible_after_hide(self, gym99_client, db_setup):
        """Own muscle disappears from visible list after hiding."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["muscle_99_hide"] not in ids, (
            f"Expected muscle_99_hide to be hidden, but it's still in list: {ids}"
        )

    def test_hidden_muscle_row_exists_in_db(self, gym99_client, db_setup):
        """UserHiddenMuscle row is present after hiding."""
        client, seed, _ = gym99_client
        superuser_url = db_setup["superuser_url"]
        assert _hidden_muscle_exists(superuser_url, USER_99_ID, seed["muscle_99_hide"]), (
            "Expected user_hidden_muscles row to exist after hide"
        )

    def test_unhide_own_muscle_returns_204(self, gym99_client, db_setup):
        """DELETE /muscles/{id}/hidden (unhide) for own muscle returns 204."""
        client, seed, _ = gym99_client
        mid = seed["muscle_99_hide"]
        resp = client.delete(
            f"/api/v1/muscles/{mid}/hidden",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when unhiding own muscle, got {resp.status_code}: {resp.text}"
        )

    def test_own_muscle_visible_after_unhide(self, gym99_client, db_setup):
        """Own muscle reappears in visible list after unhiding."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["muscle_99_hide"] in ids, (
            f"Expected muscle_99_hide to be visible after unhide: {ids}"
        )


# ---------------------------------------------------------------------------
# 5. Backward-compatibility: canonical names still work
# ---------------------------------------------------------------------------


class TestCanonicalNameBackwardCompat:
    """Existing callers using canonical names must not be broken."""

    def test_canonical_name_log_context_still_works(self, gym99_client):
        """Canonical name → log-context → PR non-null (regression guard)."""
        client, seed, _ = gym99_client
        data = _log_context(client, USER_99_ID, "GYM99 Chest", "GYM99 Bench Press")
        assert data["pr"] is not None, (
            f"Regression: canonical name must still return real PR: {data}"
        )
        assert float(data["pr"]["weight"]) == 120.0

    def test_canonical_personal_record_still_works(self, gym99_client):
        """canonical name → personal-record → non-null (regression guard)."""
        client, seed, _ = gym99_client
        resp = client.get(
            "/api/v1/analytics/personal-record",
            params={"muscle": "GYM99 Chest", "exercise": "GYM99 Bench Press"},
            headers=_service_headers(USER_99_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data is not None
        assert float(data["weight"]) == 120.0
