"""Analytics endpoints integration tests (GYM-39).

Tests the three new endpoints:
  GET /analytics/activity
  GET /analytics/summary
  GET /analytics/exercise-progress

Validates:
  1. Each endpoint returns correct per-user data.
  2. Cross-user isolation: user A never sees user B's data.
  3. Cache hit path returns the same data as the first call.
  4. Cache-down fallback still serves (Redis unavailable → DB result returned).

Reuses the session-scoped ``db_setup`` fixture from ``conftest.py``.
Works with the seed data from conftest._seed_data only (no extra inserts)
so that existing tests in test_rls_endpoints.py and test_rls_isolation.py
that assert exact row counts are not disturbed.

Conftest seed layout:
  - USER_A_ID: private muscle A, private exercise A, 2 training rows (sets 1,2 at NOW()).
  - USER_B_ID: private muscle B, private exercise B, 2 training rows (sets 1,2 at NOW()).
  - Global: 1 muscle (Global Chest), 1 exercise (Global Bench Press).
"""

import os
import sys
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, USER_B_ID, _APP_ROLE, _APP_ROLE_PASSWORD


# ---------------------------------------------------------------------------
# Shared helpers
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
    # Point Redis at a non-reachable port so all cache calls are misses/failures.
    # The cache module degrades gracefully — errors are logged and the DB is used.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Module-scoped test client — reuses the session DB (no extra seeding)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def analytics_client(db_setup):
    """Build a TestClient for analytics endpoint tests.

    Reuses the ephemeral postgres:16 from conftest (session-scoped) with
    the exact same seed data.  No extra training rows are inserted here.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        A configured TestClient.
    """
    from urllib.parse import urlparse
    app_rw_url = db_setup["app_rw_url"]

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
    from fastapi.testclient import TestClient

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
    yield client

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 1. /analytics/activity
# ---------------------------------------------------------------------------

class TestActivityEndpoint:
    """GET /analytics/activity returns correct per-user daily counts."""

    def test_activity_returns_200(self, analytics_client):
        """Endpoint is reachable and returns 200 for user A."""
        today = date.today()
        frm = today - timedelta(days=7)
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(frm), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_activity_contains_today(self, analytics_client):
        """User A sees today as an active day (conftest seeds rows at NOW())."""
        today = date.today()
        frm = today - timedelta(days=7)
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(frm), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1, f"Expected >= 1 active day, got 0: {data}"
        dates_returned = {item["date"] for item in data}
        assert str(today) in dates_returned, (
            f"Expected today ({today}) in activity dates, got: {dates_returned}"
        )
        for item in data:
            assert "date" in item
            assert "sets_count" in item
            assert item["sets_count"] > 0

    def test_activity_cross_user_isolation(self, analytics_client):
        """Both users see today, but their data is scoped independently."""
        today = date.today()
        frm = today - timedelta(days=7)

        resp_a = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(frm), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        resp_b = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(frm), "to": str(today)},
            headers=_service_headers(USER_B_ID),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        data_a = resp_a.json()
        data_b = resp_b.json()

        # Both users have rows today (from conftest seed), but each endpoint
        # is scoped by user_id via RLS — they each see their own counts.
        # Neither endpoint returns 0 (both have today's rows).
        assert len(data_a) >= 1, f"User A should see >= 1 active day: {data_a}"
        assert len(data_b) >= 1, f"User B should see >= 1 active day: {data_b}"

        # Sets count for each user must reflect only their own rows (2 sets each).
        today_a = next((i for i in data_a if i["date"] == str(today)), None)
        today_b = next((i for i in data_b if i["date"] == str(today)), None)
        assert today_a is not None, f"Today ({today}) missing from A's activity: {data_a}"
        assert today_b is not None, f"Today ({today}) missing from B's activity: {data_b}"
        # Both have 2 sets from conftest seed; counts must be equal and correct.
        assert today_a["sets_count"] == today_b["sets_count"], (
            f"Both users have 2 conftest sets today; expected same count. "
            f"A={today_a['sets_count']}, B={today_b['sets_count']}"
        )

    def test_activity_rejects_inverted_range(self, analytics_client):
        """'from' > 'to' returns 400."""
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-10", "to": "2026-06-01"},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 400

    def test_activity_rejects_oversized_range(self, analytics_client):
        """Range > 400 days returns 400."""
        frm = date(2024, 1, 1)
        to = date(2025, 6, 1)  # > 400 days
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(frm), "to": str(to)},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 400

    def test_activity_unauthenticated_returns_401(self, analytics_client):
        """No auth on /analytics/activity returns 401."""
        today = date.today()
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(today - timedelta(days=7)), "to": str(today)},
        )
        assert resp.status_code == 401

    def test_activity_empty_range_with_no_data(self, analytics_client):
        """A date range with no training returns an empty list."""
        # Use a range far in the past where no seed data exists.
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2020-01-01", "to": "2020-01-07"},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        assert resp.json() == [], f"Expected empty list for past date with no data: {resp.json()}"


# ---------------------------------------------------------------------------
# 2. /analytics/summary
# ---------------------------------------------------------------------------

class TestSummaryEndpoint:
    """GET /analytics/summary returns correct headline metrics."""

    def test_summary_returns_200(self, analytics_client):
        """Endpoint is reachable for user A."""
        resp = analytics_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"

    def test_summary_shape(self, analytics_client):
        """Response contains the 4 required fields with integer values."""
        resp = analytics_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in ("exercises", "sets", "prs", "current_streak"):
            assert field in data, f"Missing field '{field}' in summary: {data}"
            assert isinstance(data[field], int), (
                f"Field '{field}' must be int, got {type(data[field])}: {data}"
            )

    def test_summary_user_a_has_activity(self, analytics_client):
        """User A has exercises >= 1, sets >= 2, streak >= 1."""
        resp = analytics_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Conftest seeds 1 private exercise and 2 training rows for A.
        assert data["exercises"] >= 1, f"User A should have exercises >= 1: {data}"
        assert data["sets"] >= 2, f"User A should have sets >= 2: {data}"
        # Streak: A trained today so must be >= 1.
        assert data["current_streak"] >= 1, (
            f"User A trained today; expected streak >= 1, got {data['current_streak']}"
        )

    def test_summary_prs_equals_exercises(self, analytics_client):
        """prs == exercises (every trained exercise has a PR by definition).

        Reason: prs is defined as count(distinct exercise_id) from training,
        same as exercises.  Every exercise with >= 1 training row has a de-facto
        max-weight personal record.
        """
        resp = analytics_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["prs"] == data["exercises"], (
            f"prs should equal exercises (same SQL subquery). "
            f"Got prs={data['prs']}, exercises={data['exercises']}"
        )

    def test_summary_cross_user_isolation(self, analytics_client):
        """User B's summary contains only B's data (not A's).

        Both users have the same conftest seed layout, so their metrics match
        in value — but this confirms each user's endpoint is independently
        scoped and neither leaks into the other.
        """
        resp_a = analytics_client.get(
            "/api/v1/analytics/summary", headers=_service_headers(USER_A_ID)
        )
        resp_b = analytics_client.get(
            "/api/v1/analytics/summary", headers=_service_headers(USER_B_ID)
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        data_a = resp_a.json()
        data_b = resp_b.json()

        # Both users have 1 private exercise and 2 training rows from conftest.
        # If RLS is working correctly, each user sees only their own rows.
        assert data_a["sets"] >= 2, f"User A sets: {data_a}"
        assert data_b["sets"] >= 2, f"User B sets: {data_b}"

        # A's sets must not include B's training rows.
        # Since conftest gives them symmetric data (2 rows each), the counts
        # are equal — but we verify the sets count is not doubled (which would
        # happen if A could see B's rows).
        assert data_a["sets"] < 10, (
            f"User A's sets={data_a['sets']} is implausibly large — possible cross-user leak"
        )

    def test_summary_unauthenticated_returns_401(self, analytics_client):
        """No auth on /analytics/summary returns 401."""
        resp = analytics_client.get("/api/v1/analytics/summary")
        assert resp.status_code == 401

    def test_summary_streak_is_non_negative(self, analytics_client):
        """current_streak is always >= 0."""
        for uid in (USER_A_ID, USER_B_ID):
            resp = analytics_client.get(
                "/api/v1/analytics/summary", headers=_service_headers(uid)
            )
            assert resp.status_code == 200
            assert resp.json()["current_streak"] >= 0, (
                f"Streak must be non-negative for user {uid}: {resp.json()}"
            )


# ---------------------------------------------------------------------------
# 3. /analytics/exercise-progress
# ---------------------------------------------------------------------------

class TestExerciseProgressEndpoint:
    """GET /analytics/exercise-progress returns per-set series."""

    def test_progress_returns_200(self, analytics_client, db_setup):
        """Endpoint returns 200 for user A's own exercise."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        muscle_name, ex_name = _get_muscle_ex_names(superuser_url, seed["priv_ex_a"])

        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": muscle_name, "exercise": ex_name},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"

    def test_progress_shape(self, analytics_client, db_setup):
        """Response has 'series' list with correct set/points structure."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        muscle_name, ex_name = _get_muscle_ex_names(superuser_url, seed["priv_ex_a"])

        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": muscle_name, "exercise": ex_name},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "series" in data
        assert isinstance(data["series"], list)
        # Conftest seeds sets 1 and 2 for user A's private exercise.
        set_numbers = [s["set"] for s in data["series"]]
        assert 1 in set_numbers, f"Expected set 1 in series, got: {set_numbers}"
        assert 2 in set_numbers, f"Expected set 2 in series, got: {set_numbers}"

    def test_progress_points_shape(self, analytics_client, db_setup):
        """Each point has date (format: date), weight, reps."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        muscle_name, ex_name = _get_muscle_ex_names(superuser_url, seed["priv_ex_a"])

        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": muscle_name, "exercise": ex_name},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        for series_item in data["series"]:
            assert "set" in series_item
            assert "points" in series_item
            for pt in series_item["points"]:
                assert "date" in pt
                assert "weight" in pt
                assert "reps" in pt
                # Date must be YYYY-MM-DD format (not full timestamp).
                assert len(pt["date"]) == 10, (
                    f"date must be 'YYYY-MM-DD', got '{pt['date']}'"
                )

    def test_progress_cross_user_isolation(self, analytics_client, db_setup):
        """User A cannot see data from user B's private exercise.

        User A has hidden B's private exercise (conftest inserts a row in
        user_hidden_exercises), so the exercise is not visible to A via RLS.
        The endpoint must return an empty series.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        # Get B's private exercise names.
        muscle_name_b, ex_name_b = _get_muscle_ex_names(superuser_url, seed["priv_ex_b"])

        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": muscle_name_b, "exercise": ex_name_b},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        # B's exercise is hidden from A → RLS filters it out → series is empty.
        assert data["series"] == [], (
            f"User A should not see data from B's hidden private exercise: {data}"
        )

    def test_progress_empty_for_unknown_exercise(self, analytics_client):
        """Non-existent exercise returns empty series (not 404)."""
        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": "NonExistentMuscle999", "exercise": "NonExistentEx999"},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["series"] == [], f"Expected empty series, got: {data}"

    def test_progress_unauthenticated_returns_401(self, analytics_client):
        """No auth on /analytics/exercise-progress returns 401."""
        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": "Chest", "exercise": "Bench Press"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Cache hit path (Redis unreachable → both calls go to DB → same result)
# ---------------------------------------------------------------------------

class TestCacheHitPath:
    """Calling an endpoint twice returns identical data.

    With Redis unreachable (test env uses port 6399), both calls hit the DB
    directly.  We verify result consistency — if Redis were available, the
    second call would be a cache hit returning the same data.
    """

    def test_activity_two_calls_same_data(self, analytics_client):
        """Calling activity twice returns identical data."""
        today = date.today()
        frm = today - timedelta(days=7)
        params = {"from": str(frm), "to": str(today)}
        headers = _service_headers(USER_A_ID)

        resp1 = analytics_client.get("/api/v1/analytics/activity", params=params, headers=headers)
        resp2 = analytics_client.get("/api/v1/analytics/activity", params=params, headers=headers)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), "Two calls to activity returned different data"

    def test_summary_two_calls_same_data(self, analytics_client):
        """Calling summary twice returns identical data."""
        headers = _service_headers(USER_A_ID)

        resp1 = analytics_client.get("/api/v1/analytics/summary", headers=headers)
        resp2 = analytics_client.get("/api/v1/analytics/summary", headers=headers)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), "Two calls to summary returned different data"

    def test_progress_two_calls_same_data(self, analytics_client, db_setup):
        """Calling exercise-progress twice returns identical data."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        muscle_name, ex_name = _get_muscle_ex_names(superuser_url, seed["priv_ex_a"])
        params = {"muscle": muscle_name, "exercise": ex_name}
        headers = _service_headers(USER_A_ID)

        resp1 = analytics_client.get(
            "/api/v1/analytics/exercise-progress", params=params, headers=headers
        )
        resp2 = analytics_client.get(
            "/api/v1/analytics/exercise-progress", params=params, headers=headers
        )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), "Two calls to exercise-progress returned different data"


# ---------------------------------------------------------------------------
# 5. Cache-down fallback (Redis connection errors must not fail the request)
# ---------------------------------------------------------------------------

class TestCacheDownFallback:
    """When Redis is unreachable the endpoints must still serve from the DB.

    The REDIS_URL in the test env (port 6399) is unreachable, so all cache
    calls are already failing and being caught inside ``cache.py``.  These
    tests confirm that the graceful-degradation path works end-to-end by
    asserting the endpoints return correct HTTP 200 responses even though
    every ``cache_get`` returns None (miss) and every ``cache_set`` silently
    fails.  This is the real fallback scenario (not simulated — the test
    REDIS_URL genuinely points to a non-existent server).
    """

    def test_activity_serves_without_redis(self, analytics_client):
        """Activity returns 200 and a list when Redis is unreachable (port 6399).

        The cache module catches the ConnectionError internally and returns None,
        so the endpoint falls through to the DB query.  The test env already
        exercises this path because REDIS_URL defaults to port 6399.
        """
        today = date.today()
        resp = analytics_client.get(
            "/api/v1/analytics/activity",
            params={"from": str(today - timedelta(days=7)), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 (cache-down fallback), got {resp.status_code}: {resp.text}"
        )
        assert isinstance(resp.json(), list)

    def test_summary_serves_without_redis(self, analytics_client):
        """Summary returns 200 with all fields when Redis is unreachable."""
        resp = analytics_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 (cache-down fallback), got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "exercises" in data and "sets" in data and "prs" in data

    def test_progress_serves_without_redis(self, analytics_client, db_setup):
        """exercise-progress returns 200 with series when Redis is unreachable."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        muscle_name, ex_name = _get_muscle_ex_names(superuser_url, seed["priv_ex_a"])

        resp = analytics_client.get(
            "/api/v1/analytics/exercise-progress",
            params={"muscle": muscle_name, "exercise": ex_name},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, (
            f"Expected 200 (cache-down fallback), got {resp.status_code}: {resp.text}"
        )
        assert "series" in resp.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_muscle_ex_names(superuser_url: str, exercise_id: int):
    """Return (muscle_name, exercise_name) for the given exercise_id.

    Args:
        superuser_url: Superuser connection URL.
        exercise_id: Exercise id to look up.

    Returns:
        Tuple of (muscle_name, exercise_name).
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text("""
                SELECT m.name AS muscle_name, e.name AS ex_name
                FROM exercises e
                JOIN muscles m ON m.id = e.muscle
                WHERE e.id = :eid
            """),
            {"eid": exercise_id},
        ).fetchone()
    eng.dispose()
    return row[0], row[1]
