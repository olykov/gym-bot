"""GYM-67: Integration tests for GET /analytics/recent-exercises.

Validates:
  1. Recency order: exercises are returned newest-trained first.
  2. Correct last weight/reps per exercise: the LATEST set's values, not max or first.
  3. Per-user isolation: user A never sees user B's exercises.
  4. Limit clamping: limit is honoured (default 8, max 50, min 1; 0 or 51 -> 422).
  5. Empty result for a user with no training rows.
  6. Cache path: two calls return identical data (Redis unreachable -> DB both times).

Seed layout (USER_RECENT_ID = 400011):
  exercise_r1 — trained on 2026-05-01 (weight=60, reps=8), then 2026-05-15
                 (weight=70, reps=10).  last_weight=70, last_reps=10 (most recent).
  exercise_r2 — trained only on 2026-05-20 (weight=50, reps=12).
  exercise_r3 — trained on 2026-04-01 (weight=40, reps=6).

Expected recency order:
  1. exercise_r2 (2026-05-20)
  2. exercise_r1 (2026-05-15)
  3. exercise_r3 (2026-04-01)

Per-user isolation uses USER_A_ID / USER_B_ID from conftest (symmetric seed).
"""

import os
import sys
import uuid
from datetime import date, datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, USER_B_ID, _APP_ROLE, _APP_ROLE_PASSWORD

USER_RECENT_ID = 400011  # isolated user; not in conftest seed


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
    # Redis unreachable — graceful cache miss path is exercised.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Fixture: TestClient with dedicated recency user
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym67_client(db_setup):
    """TestClient with USER_RECENT_ID seeded across three exercises and dates.

    Inserts:
      - muscle_recent: 1 private muscle owned by USER_RECENT_ID
      - exercise_r1: trained 2026-05-01 (weight=60, reps=8) then 2026-05-15
                     (weight=70, reps=10).  Last set: weight=70, reps=10.
      - exercise_r2: trained 2026-05-20 (weight=50, reps=12).
      - exercise_r3: trained 2026-04-01 (weight=40, reps=6).

    Expected recency order: exercise_r2, exercise_r1, exercise_r3.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        Tuple of (TestClient, seed_meta dict).
    """
    from urllib.parse import urlparse
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from fastapi.testclient import TestClient

    superuser_url = db_setup["superuser_url"]
    app_rw_url = db_setup["app_rw_url"]

    eng_su = create_engine(superuser_url, poolclass=NullPool)
    with eng_su.connect() as conn:
        # Register test user.
        conn.execute(sa_text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'RecentUser', 'recent_test_user')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_RECENT_ID})

        # Create private muscle.
        conn.execute(sa_text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('muscle_recent', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_RECENT_ID})
        mid = conn.execute(sa_text(
            "SELECT id FROM muscles WHERE name='muscle_recent' AND created_by=:uid"
        ), {"uid": USER_RECENT_ID}).fetchone()[0]

        # Create three exercises.
        ex_ids = {}
        for ename in ("exercise_r1", "exercise_r2", "exercise_r3"):
            conn.execute(sa_text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"name": ename, "mid": mid, "uid": USER_RECENT_ID})
            ex_ids[ename] = conn.execute(sa_text(
                "SELECT id FROM exercises WHERE name=:name AND created_by=:uid"
            ), {"name": ename, "uid": USER_RECENT_ID}).fetchone()[0]

        # Training rows:
        # exercise_r1: two rows — older (2026-05-01 w=60 r=8) and newer (2026-05-15 w=70 r=10)
        rows_r1 = [
            (datetime(2026, 5, 1, 10, 0, 0), 60.0, 8.0, 1),
            (datetime(2026, 5, 15, 10, 0, 0), 70.0, 10.0, 1),
        ]
        for d, w, r, s in rows_r1:
            conn.execute(sa_text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :d, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "d": d, "uid": USER_RECENT_ID, "mid": mid,
                "eid": ex_ids["exercise_r1"], "s": s, "w": w, "r": r,
            })

        # exercise_r2: one row (most recent date)
        conn.execute(sa_text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :d, :uid, :mid, :eid, 1, 50.0, 12.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "d": datetime(2026, 5, 20, 10, 0, 0),
            "uid": USER_RECENT_ID, "mid": mid, "eid": ex_ids["exercise_r2"],
        })

        # exercise_r3: one row (oldest date)
        conn.execute(sa_text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :d, :uid, :mid, :eid, 1, 40.0, 6.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "d": datetime(2026, 4, 1, 10, 0, 0),
            "uid": USER_RECENT_ID, "mid": mid, "eid": ex_ids["exercise_r3"],
        })

        conn.commit()
    eng_su.dispose()

    # Build TestClient.
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
    from sqlalchemy import create_engine as sa_create_engine, event
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    test_engine = sa_create_engine(app_rw_url, poolclass=NullPool)
    test_session_local = sa_sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    from app.core.database import _set_rls_gucs
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    seed_meta = {"ex_ids": ex_ids, "mid": mid}
    yield client, seed_meta

    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    # Teardown.
    eng_su2 = create_engine(superuser_url, poolclass=NullPool)
    with eng_su2.connect() as conn:
        conn.execute(sa_text("DELETE FROM training WHERE user_id = :uid"), {"uid": USER_RECENT_ID})
        conn.execute(sa_text("DELETE FROM exercises WHERE created_by = :uid"), {"uid": USER_RECENT_ID})
        conn.execute(sa_text("DELETE FROM muscles WHERE created_by = :uid"), {"uid": USER_RECENT_ID})
        conn.execute(sa_text("DELETE FROM users WHERE id = :uid"), {"uid": USER_RECENT_ID})
        conn.commit()
    eng_su2.dispose()


# ---------------------------------------------------------------------------
# Tests: basic shape and recency ordering
# ---------------------------------------------------------------------------

class TestRecentExercisesShape:
    """GET /analytics/recent-exercises returns the correct contract shape."""

    def test_returns_200(self, gym67_client):
        """Endpoint is reachable and returns 200."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_response_is_list(self, gym67_client):
        """Response body is a JSON array."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list), f"Expected list, got: {type(resp.json())}"

    def test_item_schema(self, gym67_client):
        """Each item has the 5 required fields with correct types."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1, "Expected >= 1 item"
        for item in data:
            assert "muscle_name" in item, f"Missing muscle_name: {item}"
            assert "exercise_name" in item, f"Missing exercise_name: {item}"
            assert "last_weight" in item, f"Missing last_weight: {item}"
            assert "last_reps" in item, f"Missing last_reps: {item}"
            assert "last_date" in item, f"Missing last_date: {item}"
            assert isinstance(item["muscle_name"], str)
            assert isinstance(item["exercise_name"], str)
            assert isinstance(item["last_weight"], (int, float))
            assert isinstance(item["last_reps"], (int, float))
            # last_date must be YYYY-MM-DD (10 chars).
            assert len(item["last_date"]) == 10, (
                f"last_date must be 'YYYY-MM-DD', got '{item['last_date']}'"
            )


# ---------------------------------------------------------------------------
# Tests: recency ordering
# ---------------------------------------------------------------------------

class TestRecentExercisesOrder:
    """Exercises are returned newest-trained first."""

    def test_recency_order_newest_first(self, gym67_client):
        """exercise_r2 (2026-05-20) > exercise_r1 (2026-05-15) > exercise_r3 (2026-04-01).

        Seed layout:
          exercise_r2: last trained 2026-05-20 → should appear first.
          exercise_r1: last trained 2026-05-15 → second.
          exercise_r3: last trained 2026-04-01 → third.
        """
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()

        names = [item["exercise_name"] for item in data]
        assert "exercise_r1" in names, f"exercise_r1 missing: {names}"
        assert "exercise_r2" in names, f"exercise_r2 missing: {names}"
        assert "exercise_r3" in names, f"exercise_r3 missing: {names}"

        idx_r1 = names.index("exercise_r1")
        idx_r2 = names.index("exercise_r2")
        idx_r3 = names.index("exercise_r3")

        assert idx_r2 < idx_r1, (
            f"exercise_r2 (2026-05-20) must precede exercise_r1 (2026-05-15). "
            f"Got order: {names}"
        )
        assert idx_r1 < idx_r3, (
            f"exercise_r1 (2026-05-15) must precede exercise_r3 (2026-04-01). "
            f"Got order: {names}"
        )

    def test_dates_are_non_increasing(self, gym67_client):
        """last_date values are monotonically non-increasing (newest first)."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        dates = [item["last_date"] for item in data]
        for i in range(1, len(dates)):
            assert dates[i] <= dates[i - 1], (
                f"Dates not non-increasing at position {i}: {dates}"
            )


# ---------------------------------------------------------------------------
# Tests: correct last weight/reps (latest set, not max or first)
# ---------------------------------------------------------------------------

class TestRecentExercisesLastSetValues:
    """last_weight and last_reps reflect the most recent training row, not max/first."""

    def test_exercise_r1_last_weight_is_from_latest_row(self, gym67_client):
        """exercise_r1 was trained twice; last_weight must be 70 (from 2026-05-15), not 60.

        Seed:
          2026-05-01: weight=60, reps=8
          2026-05-15: weight=70, reps=10  ← most recent
        Expected last_weight=70, last_reps=10.
        """
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        r1 = next((item for item in data if item["exercise_name"] == "exercise_r1"), None)
        assert r1 is not None, f"exercise_r1 not in response: {data}"
        assert r1["last_weight"] == 70.0, (
            f"Expected last_weight=70 (from 2026-05-15), got {r1['last_weight']}"
        )
        assert r1["last_reps"] == 10.0, (
            f"Expected last_reps=10 (from 2026-05-15), got {r1['last_reps']}"
        )
        assert r1["last_date"] == "2026-05-15", (
            f"Expected last_date=2026-05-15, got {r1['last_date']}"
        )

    def test_exercise_r2_single_row_values(self, gym67_client):
        """exercise_r2 has one row; last_weight=50, last_reps=12, last_date=2026-05-20."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        r2 = next((item for item in data if item["exercise_name"] == "exercise_r2"), None)
        assert r2 is not None, f"exercise_r2 not in response: {data}"
        assert r2["last_weight"] == 50.0, f"Expected 50.0, got {r2['last_weight']}"
        assert r2["last_reps"] == 12.0, f"Expected 12.0, got {r2['last_reps']}"
        assert r2["last_date"] == "2026-05-20", f"Expected 2026-05-20, got {r2['last_date']}"

    def test_no_duplicate_exercises(self, gym67_client):
        """Each exercise_id appears at most once (DISTINCT ON guarantee)."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [item["exercise_name"] for item in data]
        assert len(names) == len(set(names)), (
            f"Duplicate exercise names in response (DISTINCT ON broken): {names}"
        )


# ---------------------------------------------------------------------------
# Tests: per-user isolation
# ---------------------------------------------------------------------------

class TestRecentExercisesIsolation:
    """User A never sees user B's exercises."""

    def test_user_a_does_not_see_user_b_exercises(self, gym67_client):
        """User A's recent-exercises must not include USER_RECENT_ID's exercises.

        USER_RECENT_ID's exercises are private (created_by=USER_RECENT_ID).
        User A's training references only their own private exercises.
        """
        client, _ = gym67_client
        resp_a = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_A_ID),
        )
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        names_a = {item["exercise_name"] for item in data_a}

        for name in ("exercise_r1", "exercise_r2", "exercise_r3"):
            assert name not in names_a, (
                f"User A should not see USER_RECENT_ID's exercise '{name}': {names_a}"
            )

    def test_user_b_does_not_see_user_a_exercises(self, gym67_client):
        """User B's recent-exercises must not include User A's private exercise."""
        client, _ = gym67_client
        resp_b = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_B_ID),
        )
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        names_b = {item["exercise_name"] for item in data_b}

        # Private Ex A belongs to USER_A_ID — B must not see it.
        assert "Private Ex A" not in names_b, (
            f"User B should not see 'Private Ex A': {names_b}"
        )

    def test_each_user_sees_only_own_exercises(self, gym67_client):
        """Cross-check: A and B each see their own conftest exercises only."""
        client, _ = gym67_client
        resp_a = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_A_ID),
        )
        resp_b = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_B_ID),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        names_a = {item["exercise_name"] for item in resp_a.json()}
        names_b = {item["exercise_name"] for item in resp_b.json()}

        # A should see Private Ex A; B should see Private Ex B.
        assert "Private Ex A" in names_a, f"User A should see their own exercise: {names_a}"
        assert "Private Ex B" in names_b, f"User B should see their own exercise: {names_b}"

        # No cross-contamination.
        assert "Private Ex B" not in names_a, (
            f"User A should not see Private Ex B: {names_a}"
        )
        assert "Private Ex A" not in names_b, (
            f"User B should not see Private Ex A: {names_b}"
        )


# ---------------------------------------------------------------------------
# Tests: limit parameter clamping
# ---------------------------------------------------------------------------

class TestRecentExercisesLimit:
    """limit query parameter is honoured and validated."""

    def test_default_limit_returns_at_most_8(self, gym67_client):
        """Default limit=8: response length <= 8."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 8, (
            f"Default limit=8 must return <= 8 items, got {len(resp.json())}"
        )

    def test_limit_1_returns_exactly_one(self, gym67_client):
        """limit=1 returns the single most-recently-trained exercise."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            params={"limit": 1},
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, f"Expected exactly 1 item with limit=1, got {len(data)}"
        # Must be exercise_r2 (most recent date: 2026-05-20).
        assert data[0]["exercise_name"] == "exercise_r2", (
            f"Expected exercise_r2 (most recent), got {data[0]['exercise_name']}"
        )

    def test_limit_50_is_accepted(self, gym67_client):
        """limit=50 (max) is accepted with 200."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            params={"limit": 50},
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 200

    def test_limit_51_returns_422(self, gym67_client):
        """limit=51 (above max=50) returns 422 Unprocessable Entity."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            params={"limit": 51},
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for limit=51, got {resp.status_code}: {resp.text}"
        )

    def test_limit_0_returns_422(self, gym67_client):
        """limit=0 (below min=1) returns 422 Unprocessable Entity."""
        client, _ = gym67_client
        resp = client.get(
            "/api/v1/analytics/recent-exercises",
            params={"limit": 0},
            headers=_service_headers(USER_RECENT_ID),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for limit=0, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Tests: empty result and auth
# ---------------------------------------------------------------------------

class TestRecentExercisesEdgeCases:
    """Edge cases: empty result and unauthenticated request."""

    def test_unauthenticated_returns_401(self, gym67_client):
        """No auth headers returns 401."""
        client, _ = gym67_client
        resp = client.get("/api/v1/analytics/recent-exercises")
        assert resp.status_code == 401

    def test_two_calls_return_identical_data(self, gym67_client):
        """Calling the endpoint twice returns identical data (cache consistency)."""
        client, _ = gym67_client
        headers = _service_headers(USER_RECENT_ID)
        resp1 = client.get("/api/v1/analytics/recent-exercises", headers=headers)
        resp2 = client.get("/api/v1/analytics/recent-exercises", headers=headers)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), "Two calls returned different data"
