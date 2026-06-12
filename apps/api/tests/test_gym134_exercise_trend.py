"""GYM-134: Integration tests for GET /analytics/exercise-trend.

Validates:
  1. ``last_session`` volume math: Σ(weight×reps) of the most recent day.
  2. ``prev_session`` selection: the day before the most recent one (not older).
  3. ``e1rm_trend``: per-session max Epley e1RM points, ascending, windowed.
  4. ``weeks`` window validation: 1..52 enforced (422 outside the range).
  5. Per-user isolation: user A never sees the trend user's data.
  6. Single-session exercise → prev_session is null.
  7. Exercise with no history → nulls + [].
  8. Cache path: two identical calls return the same result.

Seed layout (USER_ET_ID = 500013):
  muscle_et: private muscle owned by USER_ET_ID
  ex_et1:
    - OLD session  (now-70d): set1 (w=60, r=10)            volume=600,  e1rm=80.0
    - PREV session (now-14d): set1 (w=80, r=8) + set2 (w=80, r=6)
                                                            volume=1120, e1rm≈101.333
    - LAST session (now-2d):  set1 (w=85, r=8)             volume=680,  e1rm≈107.667
  ex_et2:  one session (now-5d): set1 (w=50, r=10)         volume=500
  ex_et3:  no training rows at all → nulls + []

Dates are relative to the wall clock because the e1RM window trails from now:
with the default weeks=8 (56 days) the OLD session is excluded; with weeks=52
it is included.

Per-user isolation borrows conftest USER_A_ID (symmetric seed; no ex_et1 data).
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, _APP_ROLE, _APP_ROLE_PASSWORD

USER_ET_ID = 500013          # dedicated user for exercise-trend tests

_NOW = datetime.utcnow()
OLD_DT = _NOW - timedelta(days=70)
PREV_DT = _NOW - timedelta(days=14)
LAST_DT = _NOW - timedelta(days=2)
SINGLE_DT = _NOW - timedelta(days=5)


def _epley(weight: float, reps: float) -> float:
    """Epley estimated one-rep max: weight * (1 + reps/30).

    Args:
        weight: Set weight in kg.
        reps: Set repetitions.

    Returns:
        Estimated 1RM.
    """
    return weight * (1 + reps / 30.0)


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
    # Redis unreachable — graceful cache miss path is exercised.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Fixture: TestClient with dedicated exercise-trend user
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym134_client(db_setup):
    """TestClient with USER_ET_ID seeded for exercise-trend scenarios.

    Inserts:
      - muscle_et: private muscle
      - ex_et1: three sessions — OLD (now-70d), PREV (now-14d, 2 sets),
        LAST (now-2d)
      - ex_et2: one session (now-5d) only — no prev session
      - ex_et3: no training rows at all

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        Tuple of (TestClient, meta dict with exercise names and muscle name).
    """
    from urllib.parse import urlparse
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.pool import NullPool
    from fastapi.testclient import TestClient

    superuser_url = db_setup["superuser_url"]
    app_rw_url = db_setup["app_rw_url"]

    eng_su = create_engine(superuser_url, poolclass=NullPool)
    with eng_su.connect() as conn:
        # Register test user.
        conn.execute(sa_text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'TrendUser', 'trend_test_user')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_ET_ID})

        # Private muscle.
        conn.execute(sa_text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('muscle_et', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_ET_ID})
        mid = conn.execute(sa_text(
            "SELECT id FROM muscles WHERE name='muscle_et' AND created_by=:uid"
        ), {"uid": USER_ET_ID}).fetchone()[0]

        # Three exercises.
        ex_ids = {}
        for ename in ("ex_et1", "ex_et2", "ex_et3"):
            conn.execute(sa_text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"name": ename, "mid": mid, "uid": USER_ET_ID})
            ex_ids[ename] = conn.execute(sa_text(
                "SELECT id FROM exercises WHERE name=:name AND created_by=:uid"
            ), {"name": ename, "uid": USER_ET_ID}).fetchone()[0]

        # ex_et1 — OLD (1 set), PREV (2 sets), LAST (1 set).
        et1_rows = [
            (OLD_DT, 1, 60.0, 10.0),
            (PREV_DT, 1, 80.0, 8.0),
            (PREV_DT + timedelta(minutes=1), 2, 80.0, 6.0),
            (LAST_DT, 1, 85.0, 8.0),
        ]
        for d, s, w, r in et1_rows:
            conn.execute(sa_text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :d, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "d": d, "uid": USER_ET_ID, "mid": mid,
                "eid": ex_ids["ex_et1"], "s": s, "w": w, "r": r,
            })

        # ex_et2 — single session.
        conn.execute(sa_text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :d, :uid, :mid, :eid, 1, 50.0, 10.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "d": SINGLE_DT, "uid": USER_ET_ID, "mid": mid, "eid": ex_ids["ex_et2"],
        })

        # ex_et3 — no training rows inserted at all.

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
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool as NP

    test_engine = create_engine(app_rw_url, poolclass=NP)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    from app.core.database import _set_rls_gucs
    event.listen(test_session_local, "after_begin", _set_rls_gucs)

    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = test_session_local

    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    meta = {
        "muscle": "muscle_et",
        "ex_et1": "ex_et1",
        "ex_et2": "ex_et2",
        "ex_et3": "ex_et3",
    }
    yield client, meta

    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    # Teardown.
    from sqlalchemy import create_engine as ceng
    from sqlalchemy.pool import NullPool as NP2
    eng_clean = ceng(superuser_url, poolclass=NP2)
    with eng_clean.connect() as conn:
        conn.execute(sa_text("DELETE FROM training WHERE user_id = :uid"), {"uid": USER_ET_ID})
        conn.execute(sa_text(
            "DELETE FROM exercises WHERE created_by = :uid"
        ), {"uid": USER_ET_ID})
        conn.execute(sa_text(
            "DELETE FROM muscles WHERE created_by = :uid"
        ), {"uid": USER_ET_ID})
        conn.execute(sa_text("DELETE FROM users WHERE id = :uid"), {"uid": USER_ET_ID})
        conn.commit()
    eng_clean.dispose()


# ---------------------------------------------------------------------------
# Helper to call the endpoint
# ---------------------------------------------------------------------------

def _trend(client, user_id: int, muscle: str, exercise: str, weeks: int | None = None):
    """Call GET /analytics/exercise-trend and return the response.

    Args:
        client: TestClient instance.
        user_id: User to impersonate.
        muscle: Muscle group name.
        exercise: Exercise name.
        weeks: Optional trailing window in weeks (omitted → server default 8).

    Returns:
        httpx Response.
    """
    params = {"muscle": muscle, "exercise": exercise}
    if weeks is not None:
        params["weeks"] = weeks
    return client.get(
        "/api/v1/analytics/exercise-trend",
        params=params,
        headers=_service_headers(user_id),
    )


# ---------------------------------------------------------------------------
# 1. Volume math
# ---------------------------------------------------------------------------

class TestSessionVolumes:
    """last_session / prev_session carry the correct Σ(weight×reps) per day."""

    def test_last_session_volume(self, gym134_client):
        """ex_et1 LAST session: 85×8 → volume 680."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        last = resp.json()["last_session"]
        assert last is not None
        assert last["volume"] == pytest.approx(680.0), f"last_session: {last}"
        assert last["date"] == str(LAST_DT.date()), f"last_session date: {last}"

    def test_prev_session_volume_sums_all_sets(self, gym134_client):
        """ex_et1 PREV session: 80×8 + 80×6 → volume 1120 (both sets summed)."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        prev = resp.json()["prev_session"]
        assert prev is not None
        assert prev["volume"] == pytest.approx(1120.0), f"prev_session: {prev}"
        assert prev["date"] == str(PREV_DT.date()), f"prev_session date: {prev}"

    def test_prev_session_is_second_most_recent_not_oldest(self, gym134_client):
        """prev_session must be the PREV day (now-14d), never the OLD day (now-70d)."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        prev = resp.json()["prev_session"]
        assert prev["date"] != str(OLD_DT.date()), (
            f"prev_session picked the oldest session, not the prior one: {prev}"
        )


# ---------------------------------------------------------------------------
# 2. e1RM trend
# ---------------------------------------------------------------------------

class TestE1rmTrend:
    """e1rm_trend = per-session max Epley e1RM inside the trailing window."""

    def test_default_window_excludes_old_session(self, gym134_client):
        """Default weeks=8 (56 days): OLD (now-70d) excluded → 2 points."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        trend = resp.json()["e1rm_trend"]
        assert len(trend) == 2, f"Expected 2 points in default window, got {trend}"
        dates = [p["date"] for p in trend]
        assert str(OLD_DT.date()) not in dates, f"OLD session leaked into window: {trend}"

    def test_points_ordered_ascending(self, gym134_client):
        """Trend points are ordered by date ascending."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        dates = [p["date"] for p in resp.json()["e1rm_trend"]]
        assert dates == sorted(dates), f"e1rm_trend not ascending: {dates}"

    def test_e1rm_is_per_session_max_epley(self, gym134_client):
        """PREV session point = max(80×(1+8/30), 80×(1+6/30)) ≈ 101.333."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        by_date = {p["date"]: p["e1rm"] for p in resp.json()["e1rm_trend"]}
        prev_key = str(PREV_DT.date())
        assert prev_key in by_date, f"PREV session missing from trend: {by_date}"
        assert by_date[prev_key] == pytest.approx(_epley(80.0, 8.0), rel=1e-6), (
            f"PREV e1rm should be the session max ({_epley(80.0, 8.0)}), "
            f"got {by_date[prev_key]}"
        )
        last_key = str(LAST_DT.date())
        assert by_date[last_key] == pytest.approx(_epley(85.0, 8.0), rel=1e-6)

    def test_wide_window_includes_old_session(self, gym134_client):
        """weeks=52: OLD session (now-70d) is inside the window → 3 points."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"], weeks=52)
        assert resp.status_code == 200, resp.text
        trend = resp.json()["e1rm_trend"]
        assert len(trend) == 3, f"Expected 3 points with weeks=52, got {trend}"
        by_date = {p["date"]: p["e1rm"] for p in trend}
        assert by_date[str(OLD_DT.date())] == pytest.approx(_epley(60.0, 10.0), rel=1e-6)


# ---------------------------------------------------------------------------
# 3. weeks window validation
# ---------------------------------------------------------------------------

class TestWeeksValidation:
    """weeks must be within 1..52 — out-of-range values are rejected (422)."""

    def test_weeks_zero_rejected(self, gym134_client):
        """weeks=0 → 422 (below the 1..52 range)."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"], weeks=0)
        assert resp.status_code == 422, f"Expected 422 for weeks=0, got {resp.status_code}"

    def test_weeks_above_52_rejected(self, gym134_client):
        """weeks=53 → 422 (above the 1..52 range)."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"], weeks=53)
        assert resp.status_code == 422, f"Expected 422 for weeks=53, got {resp.status_code}"

    def test_weeks_boundaries_accepted(self, gym134_client):
        """weeks=1 and weeks=52 are both accepted."""
        client, meta = gym134_client
        for weeks in (1, 52):
            resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et1"], weeks=weeks)
            assert resp.status_code == 200, f"weeks={weeks}: {resp.status_code} {resp.text}"


# ---------------------------------------------------------------------------
# 4. Single-session and empty-history exercises
# ---------------------------------------------------------------------------

class TestSparseHistory:
    """Single session → prev_session null; no history → nulls + []."""

    def test_single_session_has_no_prev(self, gym134_client):
        """ex_et2 has one session → last_session set, prev_session null."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et2"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["last_session"] is not None
        assert data["last_session"]["volume"] == pytest.approx(500.0)
        assert data["prev_session"] is None, f"Expected null prev: {data['prev_session']}"
        assert len(data["e1rm_trend"]) == 1

    def test_no_history_all_null_and_empty(self, gym134_client):
        """ex_et3 has no rows → last/prev null, e1rm_trend []."""
        client, meta = gym134_client
        resp = _trend(client, USER_ET_ID, meta["muscle"], meta["ex_et3"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["last_session"] is None
        assert data["prev_session"] is None
        assert data["e1rm_trend"] == []


# ---------------------------------------------------------------------------
# 5. Per-user isolation
# ---------------------------------------------------------------------------

class TestPerUserIsolation:
    """Other users cannot see USER_ET_ID's trend via the endpoint."""

    def test_user_a_cannot_see_trend_exercise(self, gym134_client):
        """USER_A_ID querying ex_et1 (private to USER_ET_ID) → empty result."""
        client, meta = gym134_client
        resp = _trend(client, USER_A_ID, meta["muscle"], meta["ex_et1"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["last_session"] is None, (
            f"User A should not see USER_ET_ID's sessions: {data['last_session']}"
        )
        assert data["prev_session"] is None
        assert data["e1rm_trend"] == []

    def test_unauthenticated_returns_401(self, gym134_client):
        """No auth headers → 401."""
        client, meta = gym134_client
        resp = client.get(
            "/api/v1/analytics/exercise-trend",
            params={"muscle": meta["muscle"], "exercise": meta["ex_et1"]},
        )
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"


# ---------------------------------------------------------------------------
# 6. Cache path — two calls return identical data
# ---------------------------------------------------------------------------

class TestCachePath:
    """Calling exercise-trend twice returns identical data (Redis down → DB both times)."""

    def test_two_calls_same_result(self, gym134_client):
        """Repeated exercise-trend request returns identical JSON."""
        client, meta = gym134_client
        params = {"muscle": meta["muscle"], "exercise": meta["ex_et1"]}
        headers = _service_headers(USER_ET_ID)

        resp1 = client.get("/api/v1/analytics/exercise-trend", params=params, headers=headers)
        resp2 = client.get("/api/v1/analytics/exercise-trend", params=params, headers=headers)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), (
            f"Two calls returned different data: {resp1.json()} vs {resp2.json()}"
        )
