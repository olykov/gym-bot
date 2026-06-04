"""Training history endpoint tests — GYM-47.

Tests:
  GET  /training/days       — shape, reverse-chrono, counts, window, isolation
  GET  /training/day/{date} — grouping with exercise/muscle names, sets, empty day
  DELETE /training/{id}     — removes own row; 404 cross-user; 404 unknown id
  Cache invalidation        — POST/PUT/DELETE each bust the user's analytics cache
                              (assert invalidate_user is called / keys cleared via
                               mocking since Redis is unreachable in test env)

Reuses the session-scoped ``db_setup`` fixture from conftest.py (two-user
seeded postgres:16).  Extra training rows are inserted per-test where needed
but each test class is careful not to corrupt the row counts other tests rely
on.

Conftest seed layout (relevant here):
  USER_A_ID: private muscle A (priv_muscle_a), private exercise A (priv_ex_a),
             2 training rows at NOW() (set=1,2; weight=100; reps=10).
  USER_B_ID: private muscle B (priv_muscle_b), private exercise B (priv_ex_b),
             2 training rows at NOW() (set=1,2; weight=80; reps=8).
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

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
    # Unreachable Redis — cache degrades gracefully, never raises.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Module-scoped test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def history_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient for history endpoint tests.

    Reuses the ephemeral postgres:16 from conftest (session-scoped) with
    the exact same seed data and applies the same RLS GUC wiring.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        A configured TestClient.
    """
    app_rw_url = db_setup["app_rw_url"]
    from urllib.parse import urlparse
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
    yield client

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


def _insert_training(superuser_url: str, uid: int, muscle_id: int,
                     exercise_id: int, set_num: int, when: datetime,
                     weight: float = 60.0, reps: float = 5.0) -> str:
    """Insert a training row as superuser and return its id.

    Args:
        superuser_url: Superuser DB URL.
        uid: User id for the row.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        set_num: Set number.
        when: Timestamp for the row.
        weight: Weight value.
        reps: Reps value.

    Returns:
        The new training id (hex string).
    """
    tid = uuid.uuid4().hex[:32]
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :when, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """),
            {"tid": tid, "when": when, "uid": uid, "mid": muscle_id,
             "eid": exercise_id, "s": set_num, "w": weight, "r": reps},
        )
        conn.commit()
    eng.dispose()
    return tid


def _delete_training_direct(superuser_url: str, tid: str) -> None:
    """Delete a training row directly as superuser (test cleanup).

    Args:
        superuser_url: Superuser DB URL.
        tid: Training id to delete.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("DELETE FROM training WHERE id = :tid"), {"tid": tid})
        conn.commit()
    eng.dispose()


# ---------------------------------------------------------------------------
# 1. GET /training/days — shape, reverse-chrono, counts, isolation
# ---------------------------------------------------------------------------

class TestListTrainingDays:
    """GET /training/days returns correct per-user summaries."""

    def test_returns_200(self, history_client):
        """Endpoint returns 200 for user A."""
        resp = history_client.get(
            "/api/v1/training/days",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"

    def test_shape(self, history_client):
        """Response is a list with correct field types."""
        resp = history_client.get(
            "/api/v1/training/days",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            day = data[0]
            assert "date" in day
            assert "muscles" in day
            assert "exercises_count" in day
            assert "sets_count" in day
            assert isinstance(day["muscles"], list)
            assert isinstance(day["exercises_count"], int)
            assert isinstance(day["sets_count"], int)

    def test_today_appears_with_correct_counts(self, history_client):
        """Conftest seeds 2 rows today for user A: 1 exercise, 2 sets.

        Uses datetime.utcnow().date() to match the UTC clock used by the
        DB seed (NOW()) and the endpoint's UTC day boundaries.
        """
        today = datetime.utcnow().date()
        resp = history_client.get(
            "/api/v1/training/days",
            params={"from": str(today), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        today_entry = next((d for d in data if d["date"] == str(today)), None)
        assert today_entry is not None, f"Today missing from day-list: {data}"
        assert today_entry["exercises_count"] >= 1
        assert today_entry["sets_count"] >= 2

    def test_muscle_names_are_strings(self, history_client):
        """Muscles array contains string names, not ids."""
        resp = history_client.get(
            "/api/v1/training/days",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        for day in data:
            for muscle in day["muscles"]:
                assert isinstance(muscle, str), (
                    f"Muscle entry must be a name string, got: {muscle!r}"
                )

    def test_reverse_chronological(self, history_client, db_setup):
        """Days are returned newest first."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        yesterday = datetime.utcnow() - timedelta(days=1)
        extra_id = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            3, yesterday,
        )
        try:
            resp = history_client.get(
                "/api/v1/training/days",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200
            data = resp.json()
            dates = [d["date"] for d in data]
            assert dates == sorted(dates, reverse=True), (
                f"Days must be reverse-chronological, got: {dates}"
            )
        finally:
            _delete_training_direct(superuser_url, extra_id)

    def test_cross_user_isolation(self, history_client):
        """User A does not see user B's training days.

        Uses datetime.utcnow().date() to match the UTC clock used by the
        DB seed (NOW()) and the endpoint's UTC day boundaries.
        """
        today = datetime.utcnow().date()
        resp_a = history_client.get(
            "/api/v1/training/days",
            params={"from": str(today), "to": str(today)},
            headers=_service_headers(USER_A_ID),
        )
        resp_b = history_client.get(
            "/api/v1/training/days",
            params={"from": str(today), "to": str(today)},
            headers=_service_headers(USER_B_ID),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        # Each user's day list must only reflect their own rows.
        # Both have 2 seed rows (1 exercise, 2 sets) today → counts are equal
        # but the endpoint is independently scoped by RLS.
        data_a = resp_a.json()
        data_b = resp_b.json()
        assert len(data_a) == len(data_b) == 1, (
            f"Both users should see exactly 1 day: A={data_a}, B={data_b}"
        )

        day_a = data_a[0]
        day_b = data_b[0]
        # Their muscle names differ (priv_muscle_a vs priv_muscle_b).
        assert day_a["muscles"] != day_b["muscles"], (
            f"A and B have different muscles; expected different names: "
            f"A={day_a['muscles']}, B={day_b['muscles']}"
        )

    def test_empty_window_returns_empty_list(self, history_client):
        """A date range with no training returns an empty list."""
        resp = history_client.get(
            "/api/v1/training/days",
            params={"from": "2020-01-01", "to": "2020-01-07"},
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated_returns_401(self, history_client):
        """No auth returns 401."""
        resp = history_client.get("/api/v1/training/days")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. GET /training/day/{date} — grouping, names, empty day
# ---------------------------------------------------------------------------

class TestGetTrainingDay:
    """GET /training/day/{date} returns correctly grouped exercise+set detail."""

    def test_returns_200_for_today(self, history_client):
        """Endpoint returns 200 for a day that has training."""
        resp = history_client.get(
            f"/api/v1/training/day/{date.today()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"

    def test_shape(self, history_client):
        """Response has date and exercises array; each exercise has sets."""
        resp = history_client.get(
            f"/api/v1/training/day/{date.today()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "date" in data
        assert "exercises" in data
        assert isinstance(data["exercises"], list)
        if data["exercises"]:
            ex = data["exercises"][0]
            assert "exercise_id" in ex
            assert "exercise_name" in ex
            assert "muscle_name" in ex
            assert "sets" in ex
            assert isinstance(ex["sets"], list)
            if ex["sets"]:
                s = ex["sets"][0]
                assert "training_id" in s
                assert "set" in s
                assert "weight" in s
                assert "reps" in s

    def test_muscle_and_exercise_are_names(self, history_client):
        """exercise_name and muscle_name are string names, not ids."""
        resp = history_client.get(
            f"/api/v1/training/day/{date.today()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        for ex in resp.json().get("exercises", []):
            assert isinstance(ex["exercise_name"], str)
            assert isinstance(ex["muscle_name"], str)

    def test_sets_ordered_by_set_number(self, history_client):
        """Sets within each exercise are in ascending set-number order."""
        resp = history_client.get(
            f"/api/v1/training/day/{date.today()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        for ex in resp.json().get("exercises", []):
            set_nums = [s["set"] for s in ex["sets"]]
            assert set_nums == sorted(set_nums), (
                f"Sets must be ascending: {set_nums}"
            )

    def test_empty_day_returns_empty_exercises(self, history_client):
        """A day with no training returns date + empty exercises (not 404)."""
        resp = history_client.get(
            "/api/v1/training/day/2020-01-01",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2020-01-01"
        assert data["exercises"] == []

    def test_cross_user_isolation(self, history_client, db_setup):
        """User A's day detail does not include user B's exercises.

        Uses datetime.utcnow().date() to match the UTC clock used by the
        DB seed (NOW()) and the endpoint's UTC day boundaries.
        """
        today = datetime.utcnow().date()
        resp_a = history_client.get(
            f"/api/v1/training/day/{today}",
            headers=_service_headers(USER_A_ID),
        )
        resp_b = history_client.get(
            f"/api/v1/training/day/{today}",
            headers=_service_headers(USER_B_ID),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        seed = db_setup["seed"]
        # User A should see their own private exercise, not B's.
        ex_ids_a = {ex["exercise_id"] for ex in resp_a.json().get("exercises", [])}
        ex_ids_b = {ex["exercise_id"] for ex in resp_b.json().get("exercises", [])}

        assert seed["priv_ex_a"] in ex_ids_a, (
            f"A's own exercise ({seed['priv_ex_a']}) missing: {ex_ids_a}"
        )
        assert seed["priv_ex_b"] not in ex_ids_a, (
            f"Cross-user leak: A sees B's exercise ({seed['priv_ex_b']})"
        )
        assert seed["priv_ex_b"] in ex_ids_b
        assert seed["priv_ex_a"] not in ex_ids_b

    def test_unauthenticated_returns_401(self, history_client):
        """No auth returns 401."""
        resp = history_client.get(f"/api/v1/training/day/{date.today()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. DELETE /training/{id} — own row, cross-user 404, unknown id 404
# ---------------------------------------------------------------------------

class TestDeleteTraining:
    """DELETE /training/{id} removes caller's own row; 404 for others'."""

    def test_delete_own_row_returns_204(self, history_client, db_setup):
        """Deleting own training row returns 204 and the row is gone."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            9, datetime.utcnow() - timedelta(days=10),
        )
        try:
            resp = history_client.delete(
                f"/api/v1/training/{tid}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 204, f"Expected 204: {resp.text}"

            # Verify the row is gone via superuser direct query.
            eng = create_engine(superuser_url, poolclass=NullPool)
            with eng.connect() as conn:
                count = conn.execute(
                    text("SELECT COUNT(*) FROM training WHERE id = :tid"), {"tid": tid}
                ).scalar()
            eng.dispose()
            assert count == 0, "Row still exists after DELETE"
        except Exception:
            _delete_training_direct(superuser_url, tid)
            raise

    def test_delete_unknown_id_returns_404(self, history_client):
        """Deleting a non-existent id returns 404."""
        fake_id = uuid.uuid4().hex[:32]
        resp = history_client.delete(
            f"/api/v1/training/{fake_id}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 404

    def test_delete_cross_user_returns_404(self, history_client, db_setup):
        """User A cannot delete user B's training row — returns 404."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        tid = _insert_training(
            superuser_url, USER_B_ID,
            seed["priv_muscle_b"], seed["priv_ex_b"],
            9, datetime.utcnow() - timedelta(days=11),
        )
        try:
            # User A tries to delete B's row.
            resp = history_client.delete(
                f"/api/v1/training/{tid}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 404, (
                f"Expected 404 for cross-user DELETE, got {resp.status_code}: {resp.text}"
            )

            # Row must still exist (B's row was not deleted).
            eng = create_engine(superuser_url, poolclass=NullPool)
            with eng.connect() as conn:
                count = conn.execute(
                    text("SELECT COUNT(*) FROM training WHERE id = :tid"), {"tid": tid}
                ).scalar()
            eng.dispose()
            assert count == 1, "B's row was deleted by user A — cross-user deletion bug!"
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_unauthenticated_returns_401(self, history_client):
        """DELETE with no auth returns 401."""
        resp = history_client.delete(
            f"/api/v1/training/{uuid.uuid4().hex[:32]}"
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Cache invalidation — POST/PUT/DELETE each call invalidate_user
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    """Every training mutation calls cache.invalidate_user for the principal.

    Uses unittest.mock.patch to intercept ``invalidate_user`` calls because
    Redis is unreachable in the test environment (port 6399).  We verify the
    function is called with the correct user_id on each mutation path.
    """

    def test_post_training_invalidates_cache(self, history_client, db_setup):
        """POST /training calls invalidate_user(uid) on success."""
        seed = db_setup["seed"]
        superuser_url = db_setup["superuser_url"]

        # Look up names for user A's private muscle + exercise.
        eng = create_engine(superuser_url, poolclass=NullPool)
        with eng.connect() as conn:
            row = conn.execute(text("""
                SELECT m.name AS muscle_name, e.name AS ex_name
                FROM exercises e JOIN muscles m ON m.id = e.muscle
                WHERE e.id = :eid
            """), {"eid": seed["priv_ex_a"]}).fetchone()
        eng.dispose()
        muscle_name, ex_name = row[0], row[1]

        with patch("app.api.v1.bot_router.invalidate_user") as mock_inv:
            resp = history_client.post(
                "/api/v1/training",
                json={
                    "muscle_name": muscle_name,
                    "exercise_name": ex_name,
                    "set": 99,
                    "weight": 50.0,
                    "reps": 5.0,
                },
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 201, f"POST failed: {resp.text}"
            mock_inv.assert_called_once_with(USER_A_ID)

            # Clean up the inserted row.
            created_id = resp.json()["id"]
            _delete_training_direct(superuser_url, created_id)

    def test_put_training_invalidates_cache(self, history_client, db_setup):
        """PUT /training/{id} calls invalidate_user(uid) on success."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            7, datetime.utcnow() - timedelta(days=5),
        )
        try:
            with patch("app.api.v1.bot_router.invalidate_user") as mock_inv:
                resp = history_client.put(
                    f"/api/v1/training/{tid}",
                    json={"weight": 75.0, "reps": 8.0},
                    headers=_service_headers(USER_A_ID),
                )
                assert resp.status_code == 200, f"PUT failed: {resp.text}"
                mock_inv.assert_called_once_with(USER_A_ID)
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_delete_training_invalidates_cache(self, history_client, db_setup):
        """DELETE /training/{id} calls invalidate_user(uid) on success."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            8, datetime.utcnow() - timedelta(days=6),
        )
        with patch("app.api.v1.training_history_router.invalidate_user") as mock_inv:
            resp = history_client.delete(
                f"/api/v1/training/{tid}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 204, f"DELETE failed: {resp.text}"
            mock_inv.assert_called_once_with(USER_A_ID)
