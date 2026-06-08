"""GYM-51: Integration tests for retroactive-add (date) + PATCH move.

Tests:
  1. POST /training with explicit past date -> row stored on that day at noon UTC.
  2. POST /training without date -> stored at utcnow() (unchanged behaviour).
  3. PATCH /training/{id}/move to another DATE -> day changes.
  4. PATCH /training/{id}/move to another EXERCISE (by name, variant case) -> exercise_id changes.
  5. PATCH /training/{id}/move both date + exercise at once.
  6. Empty body -> 422.
  7. Only muscle_name (no exercise_name) -> 422.
  8. Only exercise_name (no muscle_name) -> 422.
  9. Non-resolvable exercise -> 422/404.
  10. Collision: move creates duplicate set@day+exercise -> 409.
  11. Cross-user / unknown id -> 404.
  12. Cache invalidate_user called on successful move.

Seed (USER_51_ID = 500051, USER_51_B_ID = 500052):
  muscle_51:   private muscle owned by USER_51_ID
  ex_51:       private exercise under muscle_51
  muscle_51_b: private muscle owned by USER_51_B_ID
  ex_51_b:     private exercise under muscle_51_b
"""

import os
import sys
import uuid
from datetime import date, datetime, time, timedelta
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_51_ID = 500051
USER_51_B_ID = 500052


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
    # Unreachable Redis — cache degrades gracefully.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_gym51(superuser_url: str) -> dict:
    """Insert seed data for GYM-51 tests.

    Creates:
    - USER_51_ID: private muscle + exercise; no training rows yet.
    - USER_51_B_ID: private muscle + exercise; no training rows yet.
    - A second exercise under muscle_51 (ex_51_alt) for exercise-move tests.

    Args:
        superuser_url: Superuser DB URL.

    Returns:
        Dict with seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        # Users
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name)
            VALUES (:a, NOW(), 'GYM51A'), (:b, NOW(), 'GYM51B')
            ON CONFLICT (id) DO NOTHING
        """), {"a": USER_51_ID, "b": USER_51_B_ID})

        # Muscle A
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Muscle 51', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_51_ID})
        muscle_a = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Muscle 51' AND created_by=:uid"
        ), {"uid": USER_51_ID}).fetchone()[0]

        # Exercise A (primary)
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Exercise 51', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_a, "uid": USER_51_ID})
        ex_a = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Exercise 51' AND created_by=:uid"
        ), {"uid": USER_51_ID}).fetchone()[0]

        # Exercise A alt (for exercise-move target)
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Exercise 51 Alt', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_a, "uid": USER_51_ID})
        ex_a_alt = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Exercise 51 Alt' AND created_by=:uid"
        ), {"uid": USER_51_ID}).fetchone()[0]

        # Muscle B
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Muscle 51 B', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_51_B_ID})
        muscle_b = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Muscle 51 B' AND created_by=:uid"
        ), {"uid": USER_51_B_ID}).fetchone()[0]

        # Exercise B
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Exercise 51 B', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": muscle_b, "uid": USER_51_B_ID})
        ex_b = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Exercise 51 B' AND created_by=:uid"
        ), {"uid": USER_51_B_ID}).fetchone()[0]

        conn.commit()
    eng.dispose()

    return {
        "muscle_a": muscle_a,
        "ex_a": ex_a,
        "ex_a_alt": ex_a_alt,
        "muscle_b": muscle_b,
        "ex_b": ex_b,
    }


def _insert_training(
    superuser_url: str,
    uid: int,
    muscle_id: int,
    exercise_id: int,
    set_num: int,
    when: datetime,
    weight: float = 60.0,
    reps: float = 5.0,
) -> str:
    """Insert a training row directly as superuser and return its id.

    Args:
        superuser_url: Superuser DB URL.
        uid: User id.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        set_num: Set number.
        when: Timestamp.
        weight: Weight value.
        reps: Reps value.

    Returns:
        New training id (hex string).
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
    """Delete a training row as superuser (cleanup).

    Args:
        superuser_url: Superuser DB URL.
        tid: Training id to delete.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("DELETE FROM training WHERE id = :tid"), {"tid": tid})
        conn.commit()
    eng.dispose()


def _get_training_date(superuser_url: str, tid: str) -> datetime:
    """Fetch the stored datetime for a training row.

    Args:
        superuser_url: Superuser DB URL.
        tid: Training id.

    Returns:
        The datetime stored in the training.date column.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT date FROM training WHERE id = :tid"), {"tid": tid}
        ).fetchone()
    eng.dispose()
    assert row is not None, f"Training row {tid} not found"
    return row[0]


def _get_training_exercise(superuser_url: str, tid: str) -> int:
    """Fetch the exercise_id for a training row.

    Args:
        superuser_url: Superuser DB URL.
        tid: Training id.

    Returns:
        The exercise_id.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT exercise_id FROM training WHERE id = :tid"), {"tid": tid}
        ).fetchone()
    eng.dispose()
    assert row is not None, f"Training row {tid} not found"
    return row[0]


# ---------------------------------------------------------------------------
# Module-scoped test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym51_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient for GYM-51 tests with the seeded gym51 data.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        A configured TestClient with seed dict attached as client._seed51.
    """
    from urllib.parse import urlparse

    app_rw_url = db_setup["app_rw_url"]
    superuser_url = db_setup["superuser_url"]
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
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)

    # Seed GYM-51 specific data.
    seed51 = _seed_gym51(superuser_url)
    client._seed51 = seed51  # type: ignore[attr-defined]
    client._superuser_url = superuser_url  # type: ignore[attr-defined]

    yield client

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 1. Retroactive add — POST /training with explicit date
# ---------------------------------------------------------------------------

class TestRetroactiveAdd:
    """POST /training with explicit date stores row on that calendar day at noon UTC."""

    def test_create_with_past_date_stores_noon_utc(self, gym51_client, db_setup):
        """Row created with body.date is stored at noon UTC of that date."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        past_date = (datetime.utcnow() - timedelta(days=7)).date()
        expected_dt = datetime.combine(past_date, time(12, 0))

        resp = gym51_client.post(
            "/api/v1/training",
            json={
                "muscle_name": "Muscle 51",
                "exercise_name": "Exercise 51",
                "set": 1,
                "weight": 50.0,
                "reps": 5.0,
                "date": str(past_date),
            },
            headers=_service_headers(USER_51_ID),
        )
        assert resp.status_code == 201, f"POST failed: {resp.text}"
        created_id = resp.json()["id"]

        try:
            stored_dt = _get_training_date(superuser_url, created_id)
            # Truncate to minute-precision for comparison (ignore sub-second).
            stored_dt_trunc = stored_dt.replace(second=0, microsecond=0)
            expected_trunc = expected_dt.replace(second=0, microsecond=0)
            assert stored_dt_trunc == expected_trunc, (
                f"Expected noon UTC {expected_trunc}, got {stored_dt_trunc}"
            )

            # Verify it groups under the target date via the history endpoint.
            resp_days = gym51_client.get(
                "/api/v1/training/days",
                params={"from": str(past_date), "to": str(past_date)},
                headers=_service_headers(USER_51_ID),
            )
            assert resp_days.status_code == 200
            days = resp_days.json()
            assert any(d["date"] == str(past_date) for d in days), (
                f"Expected day {past_date} in history, got: {days}"
            )
        finally:
            _delete_training_direct(superuser_url, created_id)

    def test_create_without_date_uses_utcnow(self, gym51_client, db_setup):
        """Row created without body.date is stored near utcnow()."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        before = datetime.utcnow()
        resp = gym51_client.post(
            "/api/v1/training",
            json={
                "muscle_name": "Muscle 51",
                "exercise_name": "Exercise 51",
                "set": 2,
                "weight": 55.0,
                "reps": 6.0,
            },
            headers=_service_headers(USER_51_ID),
        )
        after = datetime.utcnow()
        assert resp.status_code == 201, f"POST failed: {resp.text}"
        created_id = resp.json()["id"]

        try:
            stored_dt = _get_training_date(superuser_url, created_id)
            # Must be within the before-after window (allow 5 s clock slop).
            assert before - timedelta(seconds=5) <= stored_dt <= after + timedelta(seconds=5), (
                f"Stored datetime {stored_dt} not within expected window [{before}, {after}]"
            )
        finally:
            _delete_training_direct(superuser_url, created_id)


# ---------------------------------------------------------------------------
# 2. PATCH /training/{id}/move — date move
# ---------------------------------------------------------------------------

class TestMoveDate:
    """PATCH /training/{id}/move with date changes the calendar day."""

    def test_move_to_another_date(self, gym51_client, db_setup):
        """Move a set to a different date stores it at noon UTC of the target day."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        original_dt = datetime.utcnow() - timedelta(days=3)
        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, original_dt,
        )
        target_date = (datetime.utcnow() - timedelta(days=10)).date()
        expected_dt = datetime.combine(target_date, time(12, 0))

        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={"date": str(target_date)},
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 200, f"PATCH move failed: {resp.text}"
            stored_dt = _get_training_date(superuser_url, tid)
            stored_trunc = stored_dt.replace(second=0, microsecond=0)
            expected_trunc = expected_dt.replace(second=0, microsecond=0)
            assert stored_trunc == expected_trunc, (
                f"Expected {expected_trunc}, stored {stored_trunc}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)


# ---------------------------------------------------------------------------
# 3. PATCH /training/{id}/move — exercise move
# ---------------------------------------------------------------------------

class TestMoveExercise:
    """PATCH /training/{id}/move with muscle_name+exercise_name changes exercise."""

    def test_move_to_another_exercise_by_name(self, gym51_client, db_setup):
        """Moving to another exercise changes exercise_id (exact name)."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=4),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={
                    "muscle_name": "Muscle 51",
                    "exercise_name": "Exercise 51 Alt",
                },
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 200, f"PATCH move exercise failed: {resp.text}"
            new_eid = _get_training_exercise(superuser_url, tid)
            assert new_eid == seed["ex_a_alt"], (
                f"Expected exercise_id={seed['ex_a_alt']}, got {new_eid}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_move_to_exercise_by_variant_case(self, gym51_client, db_setup):
        """Moving with variant-case name (EXERCISE 51 ALT) resolves correctly."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=5),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={
                    "muscle_name": "MUSCLE 51",
                    "exercise_name": "exercise 51 alt",
                },
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 200, f"Case-variant move failed: {resp.text}"
            new_eid = _get_training_exercise(superuser_url, tid)
            assert new_eid == seed["ex_a_alt"], (
                f"Expected exercise_id={seed['ex_a_alt']}, got {new_eid}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_move_both_date_and_exercise(self, gym51_client, db_setup):
        """Move both date and exercise at once."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=2),
        )
        target_date = (datetime.utcnow() - timedelta(days=20)).date()
        expected_dt = datetime.combine(target_date, time(12, 0))

        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={
                    "date": str(target_date),
                    "muscle_name": "Muscle 51",
                    "exercise_name": "Exercise 51 Alt",
                },
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 200, f"Combined move failed: {resp.text}"

            stored_dt = _get_training_date(superuser_url, tid)
            stored_trunc = stored_dt.replace(second=0, microsecond=0)
            assert stored_trunc == expected_dt, (
                f"Date: expected {expected_dt}, got {stored_trunc}"
            )
            new_eid = _get_training_exercise(superuser_url, tid)
            assert new_eid == seed["ex_a_alt"], (
                f"Exercise: expected {seed['ex_a_alt']}, got {new_eid}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)


# ---------------------------------------------------------------------------
# 4. Validation errors — 422
# ---------------------------------------------------------------------------

class TestMoveValidation:
    """PATCH /training/{id}/move with invalid bodies returns 422."""

    def test_empty_body_returns_422(self, gym51_client, db_setup):
        """Empty body (no fields) returns 422."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=6),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={},
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 422, f"Expected 422 for empty body: {resp.text}"
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_only_muscle_name_returns_422(self, gym51_client, db_setup):
        """Providing only muscle_name (without exercise_name) returns 422."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=7),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={"muscle_name": "Muscle 51"},
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 422, (
                f"Expected 422 for muscle_name-only: {resp.text}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_only_exercise_name_returns_422(self, gym51_client, db_setup):
        """Providing only exercise_name (without muscle_name) returns 422."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=8),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={"exercise_name": "Exercise 51 Alt"},
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 422, (
                f"Expected 422 for exercise_name-only: {resp.text}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_nonresolvable_exercise_returns_422(self, gym51_client, db_setup):
        """Moving to an exercise that doesn't exist returns 422."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=9),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={
                    "muscle_name": "Muscle 51",
                    "exercise_name": "Nonexistent Exercise ZZZ",
                },
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code in (404, 422), (
                f"Expected 404 or 422 for nonexistent exercise: {resp.text}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)


# ---------------------------------------------------------------------------
# 5. Collision — 409
# ---------------------------------------------------------------------------

class TestMoveCollision:
    """Moving a set that would duplicate an existing set@day+exercise returns 409."""

    def test_move_that_collides_returns_409(self, gym51_client, db_setup):
        """Set 1 already exists on target day+exercise → 409."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        target_date = (datetime.utcnow() - timedelta(days=30)).date()
        target_dt = datetime.combine(target_date, time(12, 0))

        # Pre-existing row at the target day+exercise, set=1.
        existing_id = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a_alt"],
            1, target_dt,
        )
        # The row to be moved — also set=1.
        moving_id = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=1),
        )

        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{moving_id}/move",
                json={
                    "date": str(target_date),
                    "muscle_name": "Muscle 51",
                    "exercise_name": "Exercise 51 Alt",
                },
                headers=_service_headers(USER_51_ID),
            )
            assert resp.status_code == 409, (
                f"Expected 409 for collision, got {resp.status_code}: {resp.text}"
            )
        finally:
            _delete_training_direct(superuser_url, existing_id)
            _delete_training_direct(superuser_url, moving_id)


# ---------------------------------------------------------------------------
# 6. Auth / ownership — 404
# ---------------------------------------------------------------------------

class TestMoveOwnership:
    """Moving a set you don't own or a nonexistent id returns 404."""

    def test_nonexistent_id_returns_404(self, gym51_client):
        """Moving a nonexistent training id returns 404."""
        fake_id = uuid.uuid4().hex[:32]
        resp = gym51_client.patch(
            f"/api/v1/training/{fake_id}/move",
            json={"date": "2024-01-01"},
            headers=_service_headers(USER_51_ID),
        )
        assert resp.status_code == 404, f"Expected 404 for unknown id: {resp.text}"

    def test_cross_user_returns_404(self, gym51_client, db_setup):
        """User A cannot move user B's training row — returns 404."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid_b = _insert_training(
            superuser_url, USER_51_B_ID,
            seed["muscle_b"], seed["ex_b"],
            1, datetime.utcnow() - timedelta(days=2),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid_b}/move",
                json={"date": "2024-01-01"},
                headers=_service_headers(USER_51_ID),  # acting as user A
            )
            assert resp.status_code == 404, (
                f"Expected 404 for cross-user move, got {resp.status_code}: {resp.text}"
            )
        finally:
            _delete_training_direct(superuser_url, tid_b)

    def test_unauthenticated_returns_401(self, gym51_client, db_setup):
        """No auth headers returns 401."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=3),
        )
        try:
            resp = gym51_client.patch(
                f"/api/v1/training/{tid}/move",
                json={"date": "2024-01-01"},
            )
            assert resp.status_code == 401, (
                f"Expected 401 for unauthenticated move, got {resp.status_code}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)


# ---------------------------------------------------------------------------
# 7. Cache invalidation
# ---------------------------------------------------------------------------

class TestMoveCacheInvalidation:
    """Successful move calls invalidate_user(uid)."""

    def test_move_invalidates_cache(self, gym51_client, db_setup):
        """PATCH /training/{id}/move calls invalidate_user on success."""
        seed = gym51_client._seed51
        superuser_url = gym51_client._superuser_url

        target_date = (datetime.utcnow() - timedelta(days=14)).date()
        tid = _insert_training(
            superuser_url, USER_51_ID,
            seed["muscle_a"], seed["ex_a"],
            1, datetime.utcnow() - timedelta(days=1),
        )
        try:
            with patch(
                "app.api.v1.training_history_router.invalidate_user"
            ) as mock_inv:
                resp = gym51_client.patch(
                    f"/api/v1/training/{tid}/move",
                    json={"date": str(target_date)},
                    headers=_service_headers(USER_51_ID),
                )
                assert resp.status_code == 200, f"PATCH move failed: {resp.text}"
                mock_inv.assert_called_once_with(USER_51_ID)
        finally:
            _delete_training_direct(superuser_url, tid)
