"""GYM-156: Timezone-aware day-detail endpoint tests.

Validates that GET /training/day/{date}?tz=<IANA> computes the day window
from LOCAL midnight boundaries, mirroring how GET /training/days groups days.

Scenarios:
1. Near-midnight set (previous UTC day, same local day) is returned for the
   LOCAL date when tz is passed, and NOT returned when tz is omitted (UTC
   window).
2. The same set is NOT returned for the UTC-neighbouring UTC date when tz
   is passed (no double-counting / bleeding).
3. A DST-offset timezone (America/New_York, UTC-4 in summer) correctly
   includes a set stored at UTC 03:30 on day D+1 when fetching day D with tz.
4. Invalid tz returns HTTP 422.
5. No-tz back-compat: the endpoint still returns UTC-bounded results without tz.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Generator

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

# Isolated user ids — must not collide with other test modules.
USER_TZ156_A = 300156
USER_TZ156_B = 300157  # DST tz user


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
            {
                "tid": tid, "when": when, "uid": uid,
                "mid": muscle_id, "eid": exercise_id,
                "s": set_num, "w": weight, "r": reps,
            },
        )
        conn.commit()
    eng.dispose()
    return tid


def _delete_rows(superuser_url: str, uid: int) -> None:
    """Delete all training rows and the user record for uid.

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
        """), {"uid": uid, "name": name, "uname": f"tz156_test_{uid}"})
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
        Tuple of (TestClient, test_engine, db_module, original_session_local).
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
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    return client, test_engine, db_module, original_session_local


# ---------------------------------------------------------------------------
# Module-scoped fixture: seed near-midnight training rows
# ---------------------------------------------------------------------------
#
# Seed plan (all UTC timestamps, naive):
#
# USER_TZ156_A — Asia/Tbilisi (UTC+4):
#   Row 1: 2026-06-04 20:02 UTC  = 2026-06-05 00:02 Tbilisi  -> local date Jun 5
#   Row 2: 2026-06-05 12:00 UTC  = 2026-06-05 16:00 Tbilisi  -> local date Jun 5
#   Row 3: 2026-06-06 00:30 UTC  = 2026-06-06 04:30 Tbilisi  -> local date Jun 6 (not Jun 5)
#
# USER_TZ156_B — America/New_York (UTC-4 in summer, DST active):
#   Row 1: 2026-06-08 03:30 UTC  = 2026-06-07 23:30 America/New_York -> local Jun 7

@pytest.fixture(scope="module")
def tz156_client(db_setup) -> Generator:
    """Build a TestClient and seed near-midnight training rows for GYM-156.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        Tuple of (TestClient, superuser_url, ex_id, muscle_id).
    """
    superuser_url = db_setup["superuser_url"]

    _register_user(superuser_url, USER_TZ156_A, "Tz156UserA")
    _register_user(superuser_url, USER_TZ156_B, "Tz156UserB")

    ex_id, muscle_id = _get_global_exercise(superuser_url)

    # USER_TZ156_A rows (Tbilisi, UTC+4)
    # Row 1: 2026-06-04 20:02 UTC = 2026-06-05 00:02 Tbilisi -> local Jun 5
    _insert_training_row(
        superuser_url, USER_TZ156_A, muscle_id, ex_id, 1,
        datetime(2026, 6, 4, 20, 2, 0), weight=80.0,
    )
    # Row 2: 2026-06-05 12:00 UTC = 2026-06-05 16:00 Tbilisi -> local Jun 5
    _insert_training_row(
        superuser_url, USER_TZ156_A, muscle_id, ex_id, 2,
        datetime(2026, 6, 5, 12, 0, 0), weight=85.0,
    )
    # Row 3: 2026-06-06 00:30 UTC = 2026-06-06 04:30 Tbilisi -> local Jun 6
    _insert_training_row(
        superuser_url, USER_TZ156_A, muscle_id, ex_id, 3,
        datetime(2026, 6, 6, 0, 30, 0), weight=90.0,
    )

    # USER_TZ156_B rows (America/New_York, UTC-4 summer)
    # Row 1: 2026-06-08 03:30 UTC = 2026-06-07 23:30 America/New_York -> local Jun 7
    _insert_training_row(
        superuser_url, USER_TZ156_B, muscle_id, ex_id, 1,
        datetime(2026, 6, 8, 3, 30, 0), weight=70.0,
    )

    client, test_engine, db_module, original_session_local = _build_test_client(db_setup)

    yield client, superuser_url, ex_id, muscle_id

    # Teardown
    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    _delete_rows(superuser_url, USER_TZ156_A)
    _delete_rows(superuser_url, USER_TZ156_B)


# ---------------------------------------------------------------------------
# 1. Near-midnight set — local date includes it, UTC date does not
# ---------------------------------------------------------------------------

class TestNearMidnightTbilisi:
    """Row at 2026-06-04 20:02 UTC = 2026-06-05 00:02 Tbilisi.

    With tz=Asia/Tbilisi the window for Jun 5 is
    [2026-06-04 20:00 UTC, 2026-06-05 20:00 UTC), which includes 20:02.
    Without tz the window is [2026-06-05 00:00 UTC, 2026-06-06 00:00 UTC), which
    does not include 20:02 Jun 4 UTC.
    """

    TZ = "Asia/Tbilisi"
    NEAR_MIDNIGHT_WEIGHT = 80.0   # weight=80, set stored at 2026-06-04 20:02 UTC

    def test_near_midnight_set_returned_for_local_date_with_tz(self, tz156_client):
        """With tz=Asia/Tbilisi, Jun-5 detail includes the 00:02 local set (80 kg)."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            params={"tz": self.TZ},
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [
            s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]
        ]
        assert self.NEAR_MIDNIGHT_WEIGHT in all_weights, (
            f"Near-midnight set (weight={self.NEAR_MIDNIGHT_WEIGHT}) must appear "
            f"on local Jun-5 with tz={self.TZ}. Got weights: {all_weights}"
        )

    def test_near_midnight_set_not_returned_for_utc_jun5_without_tz(self, tz156_client):
        """Without tz, Jun-5 UTC window excludes 20:02 Jun-4 UTC (80 kg)."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [
            s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]
        ]
        assert self.NEAR_MIDNIGHT_WEIGHT not in all_weights, (
            f"Near-midnight set (80 kg, stored 2026-06-04 20:02 UTC) must NOT appear "
            f"on UTC Jun-5 without tz. Got weights: {all_weights}"
        )

    def test_near_midnight_set_returned_for_utc_jun4_without_tz(self, tz156_client):
        """Without tz, Jun-4 UTC window [Jun-4 00:00, Jun-5 00:00) includes 20:02 Jun-4."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-04",
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [
            s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]
        ]
        assert self.NEAR_MIDNIGHT_WEIGHT in all_weights, (
            f"Near-midnight set (80 kg, Jun-4 20:02 UTC) must appear on UTC Jun-4 "
            f"without tz. Got weights: {all_weights}"
        )

    def test_near_midnight_set_not_returned_for_local_jun4_with_tz(self, tz156_client):
        """With tz=Asia/Tbilisi, Jun-4 window ends at Jun-4 20:00 UTC — excludes 20:02."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-04",
            params={"tz": self.TZ},
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [
            s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]
        ]
        assert self.NEAR_MIDNIGHT_WEIGHT not in all_weights, (
            f"Near-midnight set (local Jun-5 00:02 Tbilisi) must NOT appear on "
            f"local Jun-4 with tz={self.TZ}. Got weights: {all_weights}"
        )

    def test_midday_set_on_jun5_both_with_and_without_tz(self, tz156_client):
        """The 12:00 UTC set (85 kg) appears on Jun-5 with and without tz."""
        client, *_ = tz156_client
        MIDDAY_WEIGHT = 85.0
        for params in ({}, {"tz": self.TZ}):
            resp = client.get(
                "/api/v1/training/day/2026-06-05",
                params=params,
                headers=_service_headers(USER_TZ156_A),
            )
            assert resp.status_code == 200
            all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
            assert MIDDAY_WEIGHT in all_weights, (
                f"Midday set (85 kg) must appear on Jun-5 with params={params}. "
                f"Got weights: {all_weights}"
            )

    def test_local_jun5_with_tz_does_not_bleed_into_jun6(self, tz156_client):
        """With tz=Asia/Tbilisi, Jun-5 detail does not include Jun-6 local sets (90 kg)."""
        client, *_ = tz156_client
        JUN6_WEIGHT = 90.0
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            params={"tz": self.TZ},
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert JUN6_WEIGHT not in all_weights, (
            f"Jun-6 set (90 kg) must NOT appear on local Jun-5 with tz={self.TZ}. "
            f"Got weights: {all_weights}"
        )


# ---------------------------------------------------------------------------
# 2. DST-offset timezone (America/New_York, UTC-4 summer)
# ---------------------------------------------------------------------------

class TestDSTTimezone:
    """Row at 2026-06-08 03:30 UTC = 2026-06-07 23:30 America/New_York (UTC-4 DST).

    With tz=America/New_York the window for Jun 7 is
    [2026-06-07 04:00 UTC, 2026-06-08 04:00 UTC), which includes 03:30 Jun 8 UTC.
    Without tz the window for Jun 7 is [Jun-7 00:00 UTC, Jun-8 00:00 UTC), which
    does not include 03:30 Jun 8.
    """

    TZ = "America/New_York"
    DST_SET_WEIGHT = 70.0   # stored at 2026-06-08 03:30 UTC = 2026-06-07 23:30 local

    def test_dst_set_returned_for_local_jun7_with_tz(self, tz156_client):
        """With tz=America/New_York, Jun-7 detail includes 23:30 local (03:30 UTC Jun 8)."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-07",
            params={"tz": self.TZ},
            headers=_service_headers(USER_TZ156_B),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert self.DST_SET_WEIGHT in all_weights, (
            f"DST set (70 kg, 2026-06-08 03:30 UTC = 2026-06-07 23:30 {self.TZ}) "
            f"must appear on local Jun-7. Got weights: {all_weights}"
        )

    def test_dst_set_not_returned_for_utc_jun7_without_tz(self, tz156_client):
        """Without tz, Jun-7 UTC window excludes 03:30 Jun-8 UTC."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-07",
            headers=_service_headers(USER_TZ156_B),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert self.DST_SET_WEIGHT not in all_weights, (
            f"DST set (03:30 UTC Jun 8) must NOT appear on UTC Jun-7 without tz. "
            f"Got weights: {all_weights}"
        )

    def test_dst_set_returned_for_utc_jun8_without_tz(self, tz156_client):
        """Without tz, Jun-8 UTC window [Jun-8 00:00, Jun-9 00:00) includes 03:30 Jun-8."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-08",
            headers=_service_headers(USER_TZ156_B),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert self.DST_SET_WEIGHT in all_weights, (
            f"DST set (03:30 UTC Jun 8) must appear on UTC Jun-8 without tz. "
            f"Got weights: {all_weights}"
        )

    def test_dst_set_not_returned_for_local_jun8_with_tz(self, tz156_client):
        """With tz=America/New_York, Jun-8 window starts at 04:00 UTC — excludes 03:30."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-08",
            params={"tz": self.TZ},
            headers=_service_headers(USER_TZ156_B),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert self.DST_SET_WEIGHT not in all_weights, (
            f"Jun-7 local set (70 kg) must NOT appear on local Jun-8 with "
            f"tz={self.TZ}. Got weights: {all_weights}"
        )


# ---------------------------------------------------------------------------
# 3. Invalid tz returns 422
# ---------------------------------------------------------------------------

class TestInvalidTzDay:
    """GET /training/day/{date} returns 422 for an unrecognised timezone name."""

    def test_invalid_tz_returns_422(self, tz156_client):
        """Unrecognised timezone string returns HTTP 422."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            params={"tz": "Not/AZone"},
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for 'Not/AZone', got {resp.status_code}: {resp.text}"
        )

    def test_garbage_tz_returns_422(self, tz156_client):
        """Garbage tz string returns HTTP 422."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            params={"tz": "Europe/Fakecity"},
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for 'Europe/Fakecity', got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 4. No-tz back-compat: existing UTC behaviour is unchanged
# ---------------------------------------------------------------------------

class TestNoTzBackCompat:
    """Without tz, the endpoint uses UTC windows — existing behaviour preserved."""

    def test_no_tz_returns_200(self, tz156_client):
        """Without tz, the endpoint returns 200 as before."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200, f"Expected 200: {resp.text}"

    def test_no_tz_utc_window_includes_midday_excludes_near_midnight(self, tz156_client):
        """Without tz, Jun-5 window includes 12:00 UTC (85 kg) and excludes 20:02 Jun-4 (80 kg)."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200
        all_weights = [s["weight"] for ex in resp.json()["exercises"] for s in ex["sets"]]
        assert 85.0 in all_weights, (
            f"Midday set (85 kg) must appear on UTC Jun-5 without tz. "
            f"Got weights: {all_weights}"
        )
        assert 80.0 not in all_weights, (
            f"Near-midnight set (80 kg, Jun-4 20:02 UTC) must NOT appear on UTC "
            f"Jun-5 without tz. Got weights: {all_weights}"
        )

    def test_response_has_exercises_list(self, tz156_client):
        """Response shape includes an exercises list."""
        client, *_ = tz156_client
        resp = client.get(
            "/api/v1/training/day/2026-06-05",
            headers=_service_headers(USER_TZ156_A),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "exercises" in data
        assert isinstance(data["exercises"], list)
