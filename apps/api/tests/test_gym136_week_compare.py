"""GYM-136: Integration tests for GET /analytics/week-compare and
the GYM-136 ``has_pr`` field on GET /training/days.

Week-compare validates:
  1. this_week / last_week sets+volume math (calendar weeks, Monday-start).
  2. Rows older than last week are excluded entirely.
  3. Monday rollover with a tz: a set logged Sunday 22:00 UTC belongs to the
     UTC last_week, but in UTC+14 ("Etc/GMT-14") its local wall-clock is
     Monday — the week assignment shifts (expected bucket computed in the
     test with independent zoneinfo arithmetic).
  4. Empty weeks → zeros (user with no rows at all).
  5. Per-user isolation: a fresh user sees zeros while the seeded user
     has data.
  6. 401 without auth; 422 invalid tz.

has_pr validates (semantic: "the day holds the CURRENT all-time max-weight
set of some exercise" — current-max, not was-PR-at-the-time):
  1. The day holding an exercise's standing max → has_pr True.
  2. A day whose former PR was beaten by a later day → has_pr False
     (the marker MOVES to the later day).
  3. Multi-exercise day: any one standing record marks the day.
  4. A day with only sub-max sets → False.
  5. User with no rows → [].

Seed layout:
  USER_WC_ID  (500014) — week-compare math:
    this week:  this_monday 08:00 (w=100,r=10) + 09:00 (w=50,r=10)
                → sets 2, volume 1500
    last week:  this_monday-3d 10:00 (w=80,r=10) → sets 1, volume 800
    excluded:   this_monday-10d (w=70,r=10)
  USER_WB_ID  (500017) — Monday-rollover boundary:
    one row at this_monday - 2h (Sunday 22:00 UTC, w=60,r=10, volume 600)
  USER_PR_ID  (500015) — has_pr:
    day1 (now-10d): ex_pa 100×10           → False (beaten later)
    day2 (now-5d):  ex_pa 110×8 + ex_pb 50×10 → True (both standing maxes)
    day3 (now-2d):  ex_pa 90×10 + ex_pb 40×10 → False (all sub-max)
  USER_EMPTY_ID (500016) — registered, zero training rows.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_WC_ID = 500014      # week-compare math user
USER_PR_ID = 500015      # has_pr user
USER_EMPTY_ID = 500016   # registered, no training (empty + isolation)
USER_WB_ID = 500017      # Monday-rollover boundary user

_NOW = datetime.utcnow()
THIS_MONDAY = (_NOW - timedelta(days=_NOW.weekday())).replace(
    hour=0, minute=0, second=0, microsecond=0
)

# Week-compare seed instants (naive UTC, matching the training table).
WC_THIS_1 = THIS_MONDAY + timedelta(hours=8)            # this week
WC_THIS_2 = THIS_MONDAY + timedelta(hours=9)            # this week
WC_LAST_1 = THIS_MONDAY - timedelta(days=3) + timedelta(hours=10)  # last week
WC_OLD = THIS_MONDAY - timedelta(days=10)               # excluded
WB_BOUNDARY = THIS_MONDAY - timedelta(hours=2)          # Sunday 22:00 UTC

# has_pr seed days.
PR_DAY1 = _NOW - timedelta(days=10)
PR_DAY2 = _NOW - timedelta(days=5)
PR_DAY3 = _NOW - timedelta(days=2)

# UTC+14 — the easternmost real offset; "Etc/GMT-14" is POSIX-inverted.
BOUNDARY_TZ = "Etc/GMT-14"


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


def _expected_tz_bucket(row_utc: datetime, tz_name: str) -> str:
    """Independent (test-side) week assignment for a UTC instant in a tz.

    Mirrors the contract semantics with plain zoneinfo arithmetic — NOT the
    server implementation: convert the instant to local wall-clock, find the
    Monday of its week, compare to the Monday of "today" in that tz.

    Args:
        row_utc: Naive-UTC instant of the training row.
        tz_name: IANA timezone name.

    Returns:
        "this" | "last" | "out".
    """
    tz = ZoneInfo(tz_name)
    local_date = row_utc.replace(tzinfo=timezone.utc).astimezone(tz).date()
    row_monday = local_date - timedelta(days=local_date.weekday())
    today_local = datetime.now(tz).date()
    this_monday = today_local - timedelta(days=today_local.weekday())
    if row_monday == this_monday:
        return "this"
    if row_monday == this_monday - timedelta(weeks=1):
        return "last"
    return "out"


# ---------------------------------------------------------------------------
# Fixture: TestClient with the four GYM-136 users seeded
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym136_client(db_setup):
    """TestClient with USER_WC/PR/EMPTY/WB seeded for GYM-136 scenarios.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral test DB.

    Yields:
        Tuple of (TestClient, meta dict with muscle/exercise names).
    """
    from urllib.parse import urlparse
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.pool import NullPool
    from fastapi.testclient import TestClient

    superuser_url = db_setup["superuser_url"]
    app_rw_url = db_setup["app_rw_url"]
    all_users = (USER_WC_ID, USER_PR_ID, USER_EMPTY_ID, USER_WB_ID)

    eng_su = create_engine(superuser_url, poolclass=NullPool)
    with eng_su.connect() as conn:
        for uid in all_users:
            conn.execute(sa_text("""
                INSERT INTO users (id, registration_date, first_name, username)
                VALUES (:uid, NOW(), 'WcUser', :uname)
                ON CONFLICT (id) DO NOTHING
            """), {"uid": uid, "uname": f"wc_test_user_{uid}"})

        def _mk_muscle(name: str, uid: int) -> int:
            conn.execute(sa_text("""
                INSERT INTO muscles (name, is_global, created_by)
                VALUES (:name, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"name": name, "uid": uid})
            return conn.execute(sa_text(
                "SELECT id FROM muscles WHERE name=:name AND created_by=:uid"
            ), {"name": name, "uid": uid}).fetchone()[0]

        def _mk_exercise(name: str, mid: int, uid: int) -> int:
            conn.execute(sa_text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"name": name, "mid": mid, "uid": uid})
            return conn.execute(sa_text(
                "SELECT id FROM exercises WHERE name=:name AND created_by=:uid"
            ), {"name": name, "uid": uid}).fetchone()[0]

        def _ins(uid: int, mid: int, eid: int, d: datetime,
                 s: int, w: float, r: float) -> None:
            conn.execute(sa_text("""
                INSERT INTO training
                    (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :d, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "d": d, "uid": uid, "mid": mid, "eid": eid,
                "s": s, "w": w, "r": r,
            })

        # USER_WC — week-compare math.
        m_wc = _mk_muscle("muscle_wc", USER_WC_ID)
        e_wc = _mk_exercise("ex_wc1", m_wc, USER_WC_ID)
        _ins(USER_WC_ID, m_wc, e_wc, WC_THIS_1, 1, 100.0, 10.0)
        _ins(USER_WC_ID, m_wc, e_wc, WC_THIS_2, 2, 50.0, 10.0)
        _ins(USER_WC_ID, m_wc, e_wc, WC_LAST_1, 1, 80.0, 10.0)
        _ins(USER_WC_ID, m_wc, e_wc, WC_OLD, 1, 70.0, 10.0)

        # USER_WB — single Sunday-22:00-UTC boundary row.
        m_wb = _mk_muscle("muscle_wb", USER_WB_ID)
        e_wb = _mk_exercise("ex_wb1", m_wb, USER_WB_ID)
        _ins(USER_WB_ID, m_wb, e_wb, WB_BOUNDARY, 1, 60.0, 10.0)

        # USER_PR — has_pr days.
        m_pr = _mk_muscle("muscle_pr", USER_PR_ID)
        e_pa = _mk_exercise("ex_pa", m_pr, USER_PR_ID)
        e_pb = _mk_exercise("ex_pb", m_pr, USER_PR_ID)
        _ins(USER_PR_ID, m_pr, e_pa, PR_DAY1, 1, 100.0, 10.0)
        _ins(USER_PR_ID, m_pr, e_pa, PR_DAY2, 1, 110.0, 8.0)
        _ins(USER_PR_ID, m_pr, e_pb, PR_DAY2 + timedelta(minutes=5), 1, 50.0, 10.0)
        _ins(USER_PR_ID, m_pr, e_pa, PR_DAY3, 1, 90.0, 10.0)
        _ins(USER_PR_ID, m_pr, e_pb, PR_DAY3 + timedelta(minutes=5), 1, 40.0, 10.0)

        # USER_EMPTY — registered, no training rows at all.

        conn.commit()
    eng_su.dispose()

    # Build TestClient (gym134 pattern).
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
    yield client

    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    # Teardown.
    from sqlalchemy import create_engine as ceng
    from sqlalchemy.pool import NullPool as NP2
    eng_clean = ceng(superuser_url, poolclass=NP2)
    with eng_clean.connect() as conn:
        for uid in all_users:
            conn.execute(sa_text(
                "DELETE FROM training WHERE user_id = :uid"), {"uid": uid})
            conn.execute(sa_text(
                "DELETE FROM exercises WHERE created_by = :uid"), {"uid": uid})
            conn.execute(sa_text(
                "DELETE FROM muscles WHERE created_by = :uid"), {"uid": uid})
            conn.execute(sa_text(
                "DELETE FROM users WHERE id = :uid"), {"uid": uid})
        conn.commit()
    eng_clean.dispose()


# ---------------------------------------------------------------------------
# Helpers to call the endpoints
# ---------------------------------------------------------------------------

def _week_compare(client, user_id: int, tz: str | None = None):
    """Call GET /analytics/week-compare and return the response.

    Args:
        client: TestClient instance.
        user_id: User to impersonate.
        tz: Optional IANA timezone name.

    Returns:
        httpx Response.
    """
    params = {}
    if tz is not None:
        params["tz"] = tz
    return client.get(
        "/api/v1/analytics/week-compare",
        params=params,
        headers=_service_headers(user_id),
    )


def _days(client, user_id: int):
    """Call GET /training/days (default window) and return the response.

    Args:
        client: TestClient instance.
        user_id: User to impersonate.

    Returns:
        httpx Response.
    """
    return client.get(
        "/api/v1/training/days",
        headers=_service_headers(user_id),
    )


# ---------------------------------------------------------------------------
# 1. Week-compare math (UTC weeks)
# ---------------------------------------------------------------------------

class TestWeekCompareMath:
    """this_week / last_week carry the correct COUNT / Σ(weight×reps)."""

    def test_this_week_totals(self, gym136_client):
        """This week: 100×10 + 50×10 → sets 2, volume 1500."""
        resp = _week_compare(gym136_client, USER_WC_ID)
        assert resp.status_code == 200, resp.text
        tw = resp.json()["this_week"]
        assert tw["sets"] == 2, f"this_week: {tw}"
        assert tw["volume"] == pytest.approx(1500.0), f"this_week: {tw}"

    def test_last_week_totals(self, gym136_client):
        """Last week: 80×10 → sets 1, volume 800."""
        resp = _week_compare(gym136_client, USER_WC_ID)
        assert resp.status_code == 200, resp.text
        lw = resp.json()["last_week"]
        assert lw["sets"] == 1, f"last_week: {lw}"
        assert lw["volume"] == pytest.approx(800.0), f"last_week: {lw}"

    def test_older_rows_excluded(self, gym136_client):
        """The now-10d row (70×10=700) appears in NEITHER bucket."""
        resp = _week_compare(gym136_client, USER_WC_ID)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        total = data["this_week"]["volume"] + data["last_week"]["volume"]
        assert total == pytest.approx(2300.0), (
            f"Old row leaked into the 2-week window: {data}"
        )


# ---------------------------------------------------------------------------
# 2. Monday rollover in a non-UTC timezone
# ---------------------------------------------------------------------------

class TestMondayRolloverTz:
    """A Sunday-22:00-UTC set shifts weeks under UTC+14 grouping."""

    def test_utc_puts_boundary_row_in_last_week(self, gym136_client):
        """Without tz the row (Sunday 22:00 UTC) is in last_week."""
        resp = _week_compare(gym136_client, USER_WB_ID)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["last_week"]["sets"] == 1, f"UTC last_week: {data}"
        assert data["last_week"]["volume"] == pytest.approx(600.0)
        assert data["this_week"]["sets"] == 0, f"UTC this_week: {data}"

    def test_tz_moves_boundary_row_across_the_monday(self, gym136_client):
        """Under Etc/GMT-14 the row's local wall-clock is Monday.

        The expected bucket is computed with independent zoneinfo
        arithmetic (the tz "today" may sit in a different ISO week than
        UTC "today" near the weekend, so the bucket is derived, not
        hardcoded) — and it must DIFFER from nothing: the row is always
        inside the 2-week window for this tz.
        """
        expected = _expected_tz_bucket(WB_BOUNDARY, BOUNDARY_TZ)
        resp = _week_compare(gym136_client, USER_WB_ID, tz=BOUNDARY_TZ)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        if expected == "this":
            assert data["this_week"]["sets"] == 1, f"tz this_week: {data}"
            assert data["this_week"]["volume"] == pytest.approx(600.0)
            assert data["last_week"]["sets"] == 0
        elif expected == "last":
            assert data["last_week"]["sets"] == 1, f"tz last_week: {data}"
            assert data["last_week"]["volume"] == pytest.approx(600.0)
            assert data["this_week"]["sets"] == 0
        else:  # pragma: no cover — cannot happen for a now-2h row in UTC+14
            pytest.fail(f"Boundary row left the 2-week window: {data}")

    def test_invalid_tz_rejected(self, gym136_client):
        """An unknown tz name → 422 (mirrors summary/activity)."""
        resp = _week_compare(gym136_client, USER_WC_ID, tz="Not/AZone")
        assert resp.status_code == 422, (
            f"Expected 422 for invalid tz, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# 3. Empty weeks and isolation
# ---------------------------------------------------------------------------

class TestEmptyAndIsolation:
    """No training → zeros in both buckets; users never see each other."""

    def test_empty_user_gets_zeros(self, gym136_client):
        """USER_EMPTY (no rows) → sets 0, volume 0 in both weeks."""
        resp = _week_compare(gym136_client, USER_EMPTY_ID)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["this_week"] == {"sets": 0, "volume": 0.0}, data
        assert data["last_week"] == {"sets": 0, "volume": 0.0}, data

    def test_isolation_empty_user_despite_wc_data(self, gym136_client):
        """USER_EMPTY's zeros prove USER_WC's rows never leak across users."""
        resp_wc = _week_compare(gym136_client, USER_WC_ID)
        resp_empty = _week_compare(gym136_client, USER_EMPTY_ID)
        assert resp_wc.json()["this_week"]["sets"] > 0
        assert resp_empty.json()["this_week"]["sets"] == 0

    def test_unauthenticated_returns_401(self, gym136_client):
        """No auth headers → 401."""
        resp = gym136_client.get("/api/v1/analytics/week-compare")
        assert resp.status_code == 401, (
            f"Expected 401 without auth, got {resp.status_code}"
        )

    def test_two_calls_same_result(self, gym136_client):
        """Repeated request returns identical JSON (cache-path parity)."""
        r1 = _week_compare(gym136_client, USER_WC_ID)
        r2 = _week_compare(gym136_client, USER_WC_ID)
        assert r1.status_code == r2.status_code == 200
        assert r1.json() == r2.json()


# ---------------------------------------------------------------------------
# 4. has_pr on /training/days (current-max semantic)
# ---------------------------------------------------------------------------

class TestTrainingDaysHasPr:
    """has_pr marks days holding a CURRENT standing max-weight set."""

    def _days_by_date(self, client, user_id: int) -> dict:
        resp = _days(client, user_id)
        assert resp.status_code == 200, resp.text
        return {d["date"]: d for d in resp.json()}

    def test_day_with_standing_max_is_marked(self, gym136_client):
        """day2 holds ex_pa's 110 (current max) and ex_pb's 50 → True."""
        by_date = self._days_by_date(gym136_client, USER_PR_ID)
        key = str(PR_DAY2.date())
        assert key in by_date, f"day2 missing: {by_date}"
        assert by_date[key]["has_pr"] is True, by_date[key]

    def test_pr_moved_by_later_day(self, gym136_client):
        """day1's 100 was beaten by day2's 110 → day1 has_pr False."""
        by_date = self._days_by_date(gym136_client, USER_PR_ID)
        key = str(PR_DAY1.date())
        assert key in by_date, f"day1 missing: {by_date}"
        assert by_date[key]["has_pr"] is False, (
            f"The marker must move to the later, heavier day: {by_date[key]}"
        )

    def test_submax_day_not_marked(self, gym136_client):
        """day3 (90 and 40 — both below standing maxes) → False."""
        by_date = self._days_by_date(gym136_client, USER_PR_ID)
        key = str(PR_DAY3.date())
        assert key in by_date, f"day3 missing: {by_date}"
        assert by_date[key]["has_pr"] is False, by_date[key]

    def test_has_pr_present_on_every_day(self, gym136_client):
        """Every TrainingDay entry carries a boolean has_pr."""
        resp = _days(gym136_client, USER_PR_ID)
        assert resp.status_code == 200, resp.text
        for day in resp.json():
            assert isinstance(day.get("has_pr"), bool), day

    def test_empty_user_gets_empty_list(self, gym136_client):
        """A user with no training rows → []."""
        resp = _days(gym136_client, USER_EMPTY_ID)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []
