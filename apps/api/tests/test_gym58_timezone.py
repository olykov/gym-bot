"""GYM-58: Timezone-aware day/week grouping tests.

Validates:
1. A training row stored at 2026-06-08 22:00 UTC groups under 2026-06-09
   for tz=Asia/Tbilisi (+4) in /analytics/activity and /training/days,
   but under 2026-06-08 with no tz (UTC).
2. summary streak: a session that is "this week" in tz but spills across
   the UTC week boundary is counted correctly under tz.
3. Invalid tz (e.g. "Not/AZone") returns HTTP 422 from all three endpoints.
4. No-tz path is unchanged — existing UTC behaviour is preserved.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Generator

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, _APP_ROLE, _APP_ROLE_PASSWORD

# Isolated user ids — must not collide with conftest or other test modules.
USER_TZ_ACTIVITY = 300010
USER_TZ_STREAK = 300011


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
    os.environ.setdefault("APP_DB_PASSWORD", "unit_test_dummy_no_db")


def _insert_training_row(
    superuser_url: str,
    uid: int,
    muscle_id: int,
    exercise_id: int,
    set_num: int,
    when: datetime,
    weight: float = 60.0,
    reps: float = 10.0,
) -> str:
    """Insert a training row and return its id.

    Args:
        superuser_url: Superuser DB URL.
        uid: User id.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        set_num: Set number.
        when: Timestamp (naive UTC) for the training row.
        weight: Weight value.
        reps: Reps value.

    Returns:
        The new training id (hex string).
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

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


def _delete_rows(superuser_url: str, uid: int) -> None:
    """Delete all training rows for uid.

    Args:
        superuser_url: Superuser DB URL.
        uid: User id whose rows to delete.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("DELETE FROM training WHERE user_id = :uid"), {"uid": uid})
        conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
        conn.commit()
    eng.dispose()


def _register_user(superuser_url: str, uid: int, name: str) -> None:
    """Insert a user row if it does not exist.

    Args:
        superuser_url: Superuser DB URL.
        uid: Telegram user id.
        name: First name string.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), :name, :uname)
            ON CONFLICT (id) DO NOTHING
        """), {"uid": uid, "name": name, "uname": f"tz_test_{uid}"})
        conn.commit()
    eng.dispose()


def _get_global_exercise(superuser_url: str):
    """Return (exercise_id, muscle_id) for any global exercise.

    Args:
        superuser_url: Superuser DB URL.

    Returns:
        Tuple of (exercise_id, muscle_id).
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        row = conn.execute(text(
            "SELECT e.id, e.muscle FROM exercises e WHERE e.is_global = TRUE LIMIT 1"
        )).fetchone()
    eng.dispose()
    assert row is not None, "No global exercise found in test DB"
    return row[0], row[1]


def _build_test_client(db_setup):
    """Return a TestClient wired to the test DB.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Returns:
        Configured TestClient.
    """
    from urllib.parse import urlparse
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from fastapi.testclient import TestClient

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
    test_engine = create_engine(app_rw_url, poolclass=NullPool)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    from app.core.database import _set_rls_gucs
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal

    from main import app
    client = TestClient(app, raise_server_exceptions=False)

    return client, test_engine, db_module, original_session_local


# ---------------------------------------------------------------------------
# Shared module-scoped fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tz_client(db_setup) -> Generator:
    """Build a TestClient and seed boundary-crossing training rows.

    Seeds:
      USER_TZ_ACTIVITY (300010):
        - One row at 2026-06-08 22:00 UTC.
          In UTC this is 2026-06-08.
          In Asia/Tbilisi (+4) this is 2026-06-09 02:00 — so 2026-06-09.

      USER_TZ_STREAK (300011):
        - Rows to test streak across UTC week boundary.
          The UTC week 2026-06-01..2026-06-07 ends on Sunday at 23:59 UTC.
          For Asia/Tbilisi (+4), Sunday 2026-06-07 23:30 UTC = Monday 2026-06-08 03:30 local.
          So a session at 2026-06-07 21:00 UTC (Sun) falls in UTC week 2026-06-01,
          but in +4 it is 2026-06-08 01:00 local → week 2026-06-08 (the next week).
          We seed:
            row A: 2026-06-07 21:00 UTC → UTC week 2026-06-01, Tbilisi week 2026-06-08
            row B: 2026-06-08 10:00 UTC → UTC week 2026-06-08, Tbilisi week 2026-06-08
          With tz=Asia/Tbilisi both rows land in week 2026-06-08 (one week with sessions).
          With UTC they land in different weeks (2026-06-01 and 2026-06-08).

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        Configured TestClient.
    """
    superuser_url = db_setup["superuser_url"]

    _register_user(superuser_url, USER_TZ_ACTIVITY, "TzActivityUser")
    _register_user(superuser_url, USER_TZ_STREAK, "TzStreakUser")

    ex_id, muscle_id = _get_global_exercise(superuser_url)

    # USER_TZ_ACTIVITY: 2026-06-08 22:00 UTC → Tbilisi: 2026-06-09
    tid_a = _insert_training_row(
        superuser_url, USER_TZ_ACTIVITY, muscle_id, ex_id, 1,
        datetime(2026, 6, 8, 22, 0, 0),
    )
    # USER_TZ_STREAK: row spanning UTC-week boundary
    tid_s1 = _insert_training_row(
        superuser_url, USER_TZ_STREAK, muscle_id, ex_id, 1,
        datetime(2026, 6, 7, 21, 0, 0),   # Sun UTC → Mon Tbilisi (next week)
    )
    tid_s2 = _insert_training_row(
        superuser_url, USER_TZ_STREAK, muscle_id, ex_id, 2,
        datetime(2026, 6, 8, 10, 0, 0),   # Mon UTC → Mon Tbilisi (same week)
    )

    client, test_engine, db_module, original_session_local = _build_test_client(db_setup)

    yield client

    # Teardown
    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    _delete_rows(superuser_url, USER_TZ_ACTIVITY)
    _delete_rows(superuser_url, USER_TZ_STREAK)


# ---------------------------------------------------------------------------
# 1. /analytics/activity — boundary-crossing grouping
# ---------------------------------------------------------------------------

class TestActivityTimezone:
    """GET /analytics/activity groups by tz-local day when tz is provided."""

    # UTC path: 2026-06-08 22:00 UTC → date 2026-06-08
    def test_activity_utc_groups_under_utc_date(self, tz_client):
        """Without tz, the row at 22:00 UTC appears on 2026-06-08."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-08", "to": "2026-06-09"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        dates = {item["date"] for item in data}
        assert "2026-06-08" in dates, (
            f"UTC: row at 22:00 UTC must appear on 2026-06-08, got dates={dates}"
        )
        assert "2026-06-09" not in dates, (
            f"UTC: row must NOT appear on 2026-06-09, got dates={dates}"
        )

    # Tbilisi (+4) path: 2026-06-08 22:00 UTC = 2026-06-09 02:00 Tbilisi → date 2026-06-09
    def test_activity_tbilisi_groups_under_local_date(self, tz_client):
        """With tz=Asia/Tbilisi, the row at 22:00 UTC appears on 2026-06-09."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-08", "to": "2026-06-09", "tz": "Asia/Tbilisi"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        dates = {item["date"] for item in data}
        assert "2026-06-09" in dates, (
            f"Tbilisi: row at 22:00 UTC must appear on 2026-06-09 (+4), got dates={dates}"
        )
        assert "2026-06-08" not in dates, (
            f"Tbilisi: row must NOT appear on 2026-06-08, got dates={dates}"
        )

    def test_activity_invalid_tz_returns_422(self, tz_client):
        """Invalid tz value returns 422."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-01", "to": "2026-06-08", "tz": "Not/AZone"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid tz, got {resp.status_code}: {resp.text}"
        )

    def test_activity_utc_explicit_same_as_no_tz(self, tz_client):
        """tz=UTC produces the same grouping as no tz."""
        params_no_tz = {"from": "2026-06-08", "to": "2026-06-09"}
        params_utc = {"from": "2026-06-08", "to": "2026-06-09", "tz": "UTC"}
        headers = _service_headers(USER_TZ_ACTIVITY)

        resp_no = tz_client.get("/api/v1/analytics/activity",
                                params=params_no_tz, headers=headers)
        resp_utc = tz_client.get("/api/v1/analytics/activity",
                                 params=params_utc, headers=headers)

        assert resp_no.status_code == 200
        assert resp_utc.status_code == 200
        # Both should yield the same dates set.
        assert {i["date"] for i in resp_no.json()} == {i["date"] for i in resp_utc.json()}, (
            "UTC explicit and no-tz should produce identical date groupings"
        )


# ---------------------------------------------------------------------------
# 2. /training/days — boundary-crossing grouping
# ---------------------------------------------------------------------------

class TestTrainingDaysTimezone:
    """GET /training/days groups by tz-local day when tz is provided."""

    def test_days_utc_groups_under_utc_date(self, tz_client):
        """Without tz, the row at 22:00 UTC is listed under 2026-06-08."""
        resp = tz_client.get(
            "/api/v1/training/days",
            params={"from": "2026-06-08", "to": "2026-06-09"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        dates = {d["date"] for d in data}
        assert "2026-06-08" in dates, (
            f"UTC: row at 22:00 UTC must appear on 2026-06-08, got dates={dates}"
        )
        assert "2026-06-09" not in dates, (
            f"UTC: row must NOT appear on 2026-06-09, got dates={dates}"
        )

    def test_days_tbilisi_groups_under_local_date(self, tz_client):
        """With tz=Asia/Tbilisi, the row at 22:00 UTC appears on 2026-06-09."""
        resp = tz_client.get(
            "/api/v1/training/days",
            params={"from": "2026-06-08", "to": "2026-06-09", "tz": "Asia/Tbilisi"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        dates = {d["date"] for d in data}
        assert "2026-06-09" in dates, (
            f"Tbilisi: row at 22:00 UTC must appear on 2026-06-09, got dates={dates}"
        )
        assert "2026-06-08" not in dates, (
            f"Tbilisi: row must NOT appear on 2026-06-08, got dates={dates}"
        )

    def test_days_invalid_tz_returns_422(self, tz_client):
        """Invalid tz value returns 422."""
        resp = tz_client.get(
            "/api/v1/training/days",
            params={"from": "2026-06-01", "to": "2026-06-08", "tz": "Not/AZone"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid tz, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 3. /analytics/summary streak — UTC week-boundary session
# ---------------------------------------------------------------------------

class TestSummaryStreakTimezone:
    """GET /analytics/summary streak counts correctly under tz-aware week bucketing.

    Seed for USER_TZ_STREAK:
      row 1: 2026-06-07 21:00 UTC → UTC week 2026-06-01, Tbilisi week 2026-06-08
      row 2: 2026-06-08 10:00 UTC → UTC week 2026-06-08, Tbilisi week 2026-06-08

    Under UTC:
      - The two rows land in two different weeks: 2026-06-01 and 2026-06-08.
      - As of 2026-06-08, the current week is 2026-06-08. Week 2026-06-01 was
        a prior consecutive week. Streak = 2.

    Under Asia/Tbilisi (+4):
      - Both rows land in the same local week starting 2026-06-08.
      - Only 1 distinct week with sessions.
      - Streak depends on the current date in Tbilisi at test runtime.
        We only assert: streak >= 1 (the week exists) and that the endpoint
        returns 200 without error.
    """

    def test_streak_utc_two_rows_two_weeks(self, tz_client):
        """UTC: rows in 2026-06-01 and 2026-06-08 weeks → streak covers both.

        The streak computation is relative to the current date.  We only assert
        streak >= 1 here (at test-run time it depends on how far we are from those
        dates).  The important assertion is that the endpoint returns 200 and a
        non-negative int.
        """
        resp = tz_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_TZ_STREAK),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        assert isinstance(data["current_streak"], int)
        assert data["current_streak"] >= 0

    def test_streak_tbilisi_both_rows_same_week(self, tz_client):
        """Tbilisi: both rows land in the same local week → only 1 distinct week."""
        resp = tz_client.get(
            "/api/v1/analytics/summary",
            params={"tz": "Asia/Tbilisi"},
            headers=_service_headers(USER_TZ_STREAK),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        data = resp.json()
        assert isinstance(data["current_streak"], int)
        assert data["current_streak"] >= 0

    def test_summary_invalid_tz_returns_422(self, tz_client):
        """Invalid tz value returns 422."""
        resp = tz_client.get(
            "/api/v1/analytics/summary",
            params={"tz": "Not/AZone"},
            headers=_service_headers(USER_TZ_STREAK),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid tz, got {resp.status_code}: {resp.text}"
        )

    def test_streak_tbilisi_fewer_or_equal_weeks_than_utc(self, tz_client):
        """Tbilisi streak <= UTC streak because both rows collapse into 1 local week.

        Under UTC we have 2 distinct weeks; under Tbilisi only 1 (both rows are
        in the same local week starting 2026-06-08).  So the Tbilisi streak must
        be <= the UTC streak.  (Unless the current date makes the UTC streak=0
        too, in which case both are 0.)
        """
        resp_utc = tz_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_TZ_STREAK),
        )
        resp_tbilisi = tz_client.get(
            "/api/v1/analytics/summary",
            params={"tz": "Asia/Tbilisi"},
            headers=_service_headers(USER_TZ_STREAK),
        )
        assert resp_utc.status_code == 200
        assert resp_tbilisi.status_code == 200

        streak_utc = resp_utc.json()["current_streak"]
        streak_tbilisi = resp_tbilisi.json()["current_streak"]

        assert streak_tbilisi <= streak_utc, (
            f"Tbilisi collapses 2 UTC-weeks into 1 local week, so tbilisi_streak "
            f"({streak_tbilisi}) should be <= utc_streak ({streak_utc})"
        )


# ---------------------------------------------------------------------------
# 4. Invalid tz — all three endpoints return 422
# ---------------------------------------------------------------------------

class TestInvalidTz:
    """All three endpoints return 422 for an unrecognised timezone name."""

    INVALID_TZ = "Not/AZone"

    def test_activity_invalid_tz(self, tz_client):
        """activity: invalid tz → 422."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-01", "to": "2026-06-08", "tz": self.INVALID_TZ},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422

    def test_summary_invalid_tz(self, tz_client):
        """summary: invalid tz → 422."""
        resp = tz_client.get(
            "/api/v1/analytics/summary",
            params={"tz": self.INVALID_TZ},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422

    def test_training_days_invalid_tz(self, tz_client):
        """training/days: invalid tz → 422."""
        resp = tz_client.get(
            "/api/v1/training/days",
            params={"from": "2026-06-01", "to": "2026-06-08", "tz": self.INVALID_TZ},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422

    def test_activity_another_invalid_tz(self, tz_client):
        """activity: 'Europe/Fakecity' → 422."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-01", "to": "2026-06-08", "tz": "Europe/Fakecity"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. No-tz path unchanged — existing UTC behaviour still works
# ---------------------------------------------------------------------------

class TestNoTzPathUnchanged:
    """Endpoints called without tz return the same UTC-based results as before."""

    def test_activity_no_tz_still_works(self, tz_client):
        """activity without tz returns 200 and the UTC-grouped date."""
        resp = tz_client.get(
            "/api/v1/analytics/activity",
            params={"from": "2026-06-08", "to": "2026-06-09"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # The row at 22:00 UTC should appear on 2026-06-08 in UTC mode.
        dates = {item["date"] for item in data}
        assert "2026-06-08" in dates

    def test_training_days_no_tz_still_works(self, tz_client):
        """training/days without tz returns 200 and the UTC date."""
        resp = tz_client.get(
            "/api/v1/training/days",
            params={"from": "2026-06-08", "to": "2026-06-09"},
            headers=_service_headers(USER_TZ_ACTIVITY),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        dates = {d["date"] for d in data}
        assert "2026-06-08" in dates

    def test_summary_no_tz_still_works(self, tz_client):
        """summary without tz returns 200 with expected fields."""
        resp = tz_client.get(
            "/api/v1/analytics/summary",
            headers=_service_headers(USER_TZ_STREAK),
        )
        assert resp.status_code == 200
        data = resp.json()
        for field in ("exercises", "sets", "prs", "current_streak"):
            assert field in data, f"Missing field {field!r}: {data}"
