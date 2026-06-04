"""GYM-71: Integration tests for GET /analytics/log-context.

Validates:
  1. ``completed_sets`` correctness for the requested date.
  2. ``last_session_sets`` = the sets from the most recent PRIOR day
     (not today's, ordered by set, correct weight/reps).
  3. ``pr`` matches the personal record.
  4. Per-user isolation: user A never sees user B's data.
  5. Exercise with only today's session → last_session_sets is empty.
  6. Exercise with no history → completed_sets=[], last_session_sets=[], pr=null.
  7. Cache path: two identical calls return the same result.

Seed layout (USER_LC_ID = 500011):
  muscle_lc: private muscle owned by USER_LC_ID
  ex_lc1:
    - prior session:  2026-05-10  set1 (w=80, r=8), set2 (w=80, r=6)
    - today session:  2026-06-01  set1 (already logged)
  ex_lc2:  only one session on 2026-06-01 → no prior session
  ex_lc3:  no training rows at all → empty + pr=null

The test date (TARGET_DATE = 2026-06-01) is static so expectations are
deterministic regardless of the wall-clock date.

Per-user isolation borrows conftest USER_A_ID / USER_B_ID (symmetric seed,
neither has ex_lc1 data so their log-context for that exercise is empty).
"""

import os
import sys
import uuid
from datetime import date, datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, USER_B_ID, _APP_ROLE, _APP_ROLE_PASSWORD

USER_LC_ID = 500011          # dedicated user for log-context tests
TARGET_DATE = date(2026, 6, 1)
PRIOR_DATE = date(2026, 5, 10)


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
# Fixture: TestClient with dedicated log-context user
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gym71_client(db_setup):
    """TestClient with USER_LC_ID seeded for log-context scenarios.

    Inserts:
      - muscle_lc: private muscle
      - ex_lc1: two sessions — PRIOR_DATE (sets 1+2) and TARGET_DATE (set 1)
      - ex_lc2: one session on TARGET_DATE only (no prior session)
      - ex_lc3: no training rows at all

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
            VALUES (:uid, NOW(), 'LogCtxUser', 'logctx_test_user')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_LC_ID})

        # Private muscle.
        conn.execute(sa_text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('muscle_lc', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_LC_ID})
        mid = conn.execute(sa_text(
            "SELECT id FROM muscles WHERE name='muscle_lc' AND created_by=:uid"
        ), {"uid": USER_LC_ID}).fetchone()[0]

        # Three exercises.
        ex_ids = {}
        for ename in ("ex_lc1", "ex_lc2", "ex_lc3"):
            conn.execute(sa_text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """), {"name": ename, "mid": mid, "uid": USER_LC_ID})
            ex_ids[ename] = conn.execute(sa_text(
                "SELECT id FROM exercises WHERE name=:name AND created_by=:uid"
            ), {"name": ename, "uid": USER_LC_ID}).fetchone()[0]

        # ex_lc1 — prior session: PRIOR_DATE, set1 (w=80,r=8) + set2 (w=80,r=6)
        prior_rows = [
            (datetime(2026, 5, 10, 10, 0, 0), 1, 80.0, 8.0),
            (datetime(2026, 5, 10, 10, 1, 0), 2, 80.0, 6.0),
        ]
        for d, s, w, r in prior_rows:
            conn.execute(sa_text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :d, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """), {
                "tid": uuid.uuid4().hex[:32],
                "d": d, "uid": USER_LC_ID, "mid": mid,
                "eid": ex_ids["ex_lc1"], "s": s, "w": w, "r": r,
            })

        # ex_lc1 — today session: TARGET_DATE, set1 (w=85,r=8)
        conn.execute(sa_text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :d, :uid, :mid, :eid, 1, 85.0, 8.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "d": datetime(2026, 6, 1, 10, 0, 0),
            "uid": USER_LC_ID, "mid": mid, "eid": ex_ids["ex_lc1"],
        })

        # ex_lc2 — only TARGET_DATE session (no prior)
        conn.execute(sa_text("""
            INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
            VALUES (:tid, :d, :uid, :mid, :eid, 1, 70.0, 10.0)
            ON CONFLICT DO NOTHING
        """), {
            "tid": uuid.uuid4().hex[:32],
            "d": datetime(2026, 6, 1, 11, 0, 0),
            "uid": USER_LC_ID, "mid": mid, "eid": ex_ids["ex_lc2"],
        })

        # ex_lc3 — no training rows inserted at all.

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
        "muscle": "muscle_lc",
        "ex_lc1": "ex_lc1",
        "ex_lc2": "ex_lc2",
        "ex_lc3": "ex_lc3",
    }
    yield client, meta

    db_module.SessionLocal = original_session_local
    test_engine.dispose()

    # Teardown.
    from sqlalchemy import create_engine as ceng
    from sqlalchemy.pool import NullPool as NP2
    eng_clean = ceng(superuser_url, poolclass=NP2)
    with eng_clean.connect() as conn:
        conn.execute(sa_text("DELETE FROM training WHERE user_id = :uid"), {"uid": USER_LC_ID})
        conn.execute(sa_text(
            "DELETE FROM exercises WHERE created_by = :uid"
        ), {"uid": USER_LC_ID})
        conn.execute(sa_text(
            "DELETE FROM muscles WHERE created_by = :uid"
        ), {"uid": USER_LC_ID})
        conn.execute(sa_text("DELETE FROM users WHERE id = :uid"), {"uid": USER_LC_ID})
        conn.commit()
    eng_clean.dispose()


# ---------------------------------------------------------------------------
# Helper to call the endpoint
# ---------------------------------------------------------------------------

def _log_context(client, user_id: int, muscle: str, exercise: str, d: date) -> dict:
    """Call GET /analytics/log-context and return the JSON dict.

    Args:
        client: TestClient instance.
        user_id: User to impersonate.
        muscle: Muscle group name.
        exercise: Exercise name.
        d: Date for the log session.

    Returns:
        Parsed JSON dict.
    """
    resp = client.get(
        "/api/v1/analytics/log-context",
        params={"muscle": muscle, "exercise": exercise, "date": str(d)},
        headers=_service_headers(user_id),
    )
    return resp


# ---------------------------------------------------------------------------
# 1. completed_sets
# ---------------------------------------------------------------------------

class TestCompletedSets:
    """completed_sets contains only set numbers logged on the target date."""

    def test_completed_sets_returns_set_logged_today(self, gym71_client):
        """ex_lc1 has set=1 on TARGET_DATE → completed_sets=[1]."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["completed_sets"] == [1], (
            f"Expected completed_sets=[1] for ex_lc1 on TARGET_DATE, got {data['completed_sets']}"
        )

    def test_completed_sets_excludes_prior_day_sets(self, gym71_client):
        """Sets from PRIOR_DATE must not appear in completed_sets for TARGET_DATE."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # set=2 only exists on PRIOR_DATE; it must not appear on TARGET_DATE
        assert 2 not in data["completed_sets"], (
            f"set=2 from prior session should not be in completed_sets: {data['completed_sets']}"
        )

    def test_completed_sets_empty_for_no_session_on_date(self, gym71_client):
        """ex_lc3 has no rows at all → completed_sets=[]."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc3"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        assert resp.json()["completed_sets"] == []


# ---------------------------------------------------------------------------
# 2. last_session_sets
# ---------------------------------------------------------------------------

class TestLastSessionSets:
    """last_session_sets reflects the most recent PRIOR session's sets."""

    def test_last_session_sets_is_prior_day(self, gym71_client):
        """ex_lc1: prior session (PRIOR_DATE) has sets 1+2, not today's set."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        lss = data["last_session_sets"]
        assert len(lss) == 2, f"Expected 2 prior sets for ex_lc1, got {len(lss)}: {lss}"

    def test_last_session_sets_ordered_by_set(self, gym71_client):
        """last_session_sets is ordered ascending by set number."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        lss = resp.json()["last_session_sets"]
        set_nums = [s["set"] for s in lss]
        assert set_nums == sorted(set_nums), f"last_session_sets not ordered: {set_nums}"

    def test_last_session_sets_correct_weight_reps(self, gym71_client):
        """ex_lc1 prior sets: set1=(w=80,r=8), set2=(w=80,r=6)."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        lss = resp.json()["last_session_sets"]
        by_set = {s["set"]: s for s in lss}
        assert by_set[1]["weight"] == 80.0, f"set1 weight mismatch: {by_set[1]}"
        assert by_set[1]["reps"] == 8.0, f"set1 reps mismatch: {by_set[1]}"
        assert by_set[2]["weight"] == 80.0, f"set2 weight mismatch: {by_set[2]}"
        assert by_set[2]["reps"] == 6.0, f"set2 reps mismatch: {by_set[2]}"

    def test_last_session_sets_empty_when_only_today(self, gym71_client):
        """ex_lc2 has only a TARGET_DATE session → last_session_sets=[]."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc2"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["last_session_sets"] == [], (
            f"ex_lc2 has no prior session; expected [], got {data['last_session_sets']}"
        )

    def test_last_session_sets_empty_for_no_history(self, gym71_client):
        """ex_lc3 has no training rows → last_session_sets=[]."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc3"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        assert resp.json()["last_session_sets"] == []


# ---------------------------------------------------------------------------
# 3. pr
# ---------------------------------------------------------------------------

class TestPersonalRecord:
    """pr matches the overall maximum weight for the exercise."""

    def test_pr_not_null_when_history_exists(self, gym71_client):
        """ex_lc1 has rows → pr is not null."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        pr = resp.json()["pr"]
        assert pr is not None, f"Expected pr to be set for ex_lc1, got null"

    def test_pr_weight_is_max(self, gym71_client):
        """ex_lc1 PR weight = 85.0 (today's set, which is the max across all sessions)."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        pr = resp.json()["pr"]
        assert pr["weight"] == 85.0, (
            f"Expected PR weight=85.0 (today's max), got {pr['weight']}"
        )

    def test_pr_null_for_no_history(self, gym71_client):
        """ex_lc3 has no rows → pr=null."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc3"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        assert resp.json()["pr"] is None, (
            f"Expected pr=null for exercise with no history, got {resp.json()['pr']}"
        )


# ---------------------------------------------------------------------------
# 4. Per-user isolation
# ---------------------------------------------------------------------------

class TestPerUserIsolation:
    """User A and B cannot see USER_LC_ID's exercises via log-context."""

    def test_user_a_cannot_see_lc_exercise(self, gym71_client):
        """USER_A_ID querying ex_lc1 (private to USER_LC_ID) → empty result."""
        client, meta = gym71_client
        resp = _log_context(client, USER_A_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["completed_sets"] == [], (
            f"User A should not see USER_LC_ID's sets: {data['completed_sets']}"
        )
        assert data["last_session_sets"] == [], (
            f"User A should not see USER_LC_ID's prior session: {data['last_session_sets']}"
        )
        assert data["pr"] is None, (
            f"User A should not see USER_LC_ID's PR: {data['pr']}"
        )

    def test_user_b_cannot_see_lc_exercise(self, gym71_client):
        """USER_B_ID querying ex_lc1 (private to USER_LC_ID) → empty result."""
        client, meta = gym71_client
        resp = _log_context(client, USER_B_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["completed_sets"] == []
        assert data["last_session_sets"] == []
        assert data["pr"] is None


# ---------------------------------------------------------------------------
# 5. Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    """Response must have all three required fields with correct types."""

    def test_shape_completed_sets_is_list_of_int(self, gym71_client):
        """completed_sets is a list of ints."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        sets = resp.json()["completed_sets"]
        assert isinstance(sets, list)
        assert all(isinstance(s, int) for s in sets), f"Non-int in completed_sets: {sets}"

    def test_shape_last_session_sets_has_set_weight_reps(self, gym71_client):
        """Each last_session_sets entry has set, weight, reps fields."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        for entry in resp.json()["last_session_sets"]:
            assert "set" in entry, f"Missing 'set' in {entry}"
            assert "weight" in entry, f"Missing 'weight' in {entry}"
            assert "reps" in entry, f"Missing 'reps' in {entry}"

    def test_shape_pr_has_weight_reps_date(self, gym71_client):
        """PR entry has weight, reps, date fields."""
        client, meta = gym71_client
        resp = _log_context(client, USER_LC_ID, meta["muscle"], meta["ex_lc1"], TARGET_DATE)
        assert resp.status_code == 200, resp.text
        pr = resp.json()["pr"]
        assert pr is not None
        assert "weight" in pr
        assert "reps" in pr
        assert "date" in pr

    def test_unauthenticated_returns_401(self, gym71_client):
        """No auth headers → 401."""
        client, meta = gym71_client
        resp = client.get(
            "/api/v1/analytics/log-context",
            params={"muscle": meta["muscle"], "exercise": meta["ex_lc1"],
                    "date": str(TARGET_DATE)},
        )
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"


# ---------------------------------------------------------------------------
# 6. Cache path — two calls return identical data
# ---------------------------------------------------------------------------

class TestCachePath:
    """Calling log-context twice returns identical data (Redis unreachable → DB both times)."""

    def test_two_calls_same_result(self, gym71_client):
        """Repeated log-context request returns identical JSON."""
        client, meta = gym71_client
        params = {"muscle": meta["muscle"], "exercise": meta["ex_lc1"], "date": str(TARGET_DATE)}
        headers = _service_headers(USER_LC_ID)

        resp1 = client.get("/api/v1/analytics/log-context", params=params, headers=headers)
        resp2 = client.get("/api/v1/analytics/log-context", params=params, headers=headers)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json(), (
            f"Two calls to log-context returned different data: {resp1.json()} vs {resp2.json()}"
        )
