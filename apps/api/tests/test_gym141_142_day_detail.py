"""Integration tests for GYM-141/GYM-155 (is_pr per set) and GYM-142 (recency order).

GYM-155 — is_pr per set (temporal PR semantics, replaces GYM-141 max-weight logic):
  - First ever set of an exercise has is_pr=True.
  - A set at a strictly greater weight than any prior set has is_pr=True (weight PR).
  - A set at more reps than any prior set at the same weight has is_pr=True
    (reps-at-weight PR).
  - A tie (equal weight, equal reps) is NOT a PR — must be strictly greater.
  - A lighter set is is_pr=False.
  - Cross-user isolation: user A's history does not affect user B's PR flags.

GYM-142 — recency order:
  - The day's exercise groups are returned most-recently-logged first
    (DESC by MAX(training.date) within the day).
  - Sets within each exercise group are still in ascending set-number order.

All tests use the session-scoped ``db_setup`` fixture (ephemeral postgres:16).
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, USER_B_ID, _APP_ROLE, _APP_ROLE_PASSWORD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service_headers(user_id: int) -> dict:
    """Build service-token auth headers for the given user.

    Args:
        user_id: Telegram user id to impersonate.

    Returns:
        Header dict with X-Service-Token and X-Act-As-User.
    """
    return {
        "X-Service-Token": "test_bot_service_token_rls",
        "X-Act-As-User": str(user_id),
    }


def _ensure_env_defaults() -> None:
    """Populate mandatory env vars before importing the FastAPI app."""
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
    """Insert one training row as superuser; return its hex id.

    Args:
        superuser_url: SQLAlchemy URL with superuser credentials.
        uid: User id for the row.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        set_num: Set number.
        when: Timestamp to store in the ``date`` column.
        weight: Weight value (default 60 kg).
        reps: Reps value (default 5).

    Returns:
        The training id (32-char hex string).
    """
    tid = uuid.uuid4().hex[:32]
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO training
                    (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, :when, :uid, :mid, :eid, :s, :w, :r)
                ON CONFLICT DO NOTHING
            """),
            {
                "tid": tid,
                "when": when,
                "uid": uid,
                "mid": muscle_id,
                "eid": exercise_id,
                "s": set_num,
                "w": weight,
                "r": reps,
            },
        )
        conn.commit()
    eng.dispose()
    return tid


def _delete_training_direct(superuser_url: str, *tids: str) -> None:
    """Delete training rows by id as superuser (test cleanup).

    Args:
        superuser_url: Superuser URL.
        *tids: One or more training ids to delete.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        for tid in tids:
            conn.execute(text("DELETE FROM training WHERE id = :tid"), {"tid": tid})
        conn.commit()
    eng.dispose()


# ---------------------------------------------------------------------------
# Module-scoped test client (reuses conftest ephemeral DB)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def day_detail_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient wired to the ephemeral test DB.

    Args:
        db_setup: Session-scoped fixture from conftest providing the test DB.

    Yields:
        A configured TestClient with RLS GUC wiring.
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
    yield client

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# GYM-155 — is_pr per set (replaces GYM-141 all-time-max semantics)
# ---------------------------------------------------------------------------

class TestIsPrFlag:
    """GET /training/day/{date} correctly sets is_pr on each set (GYM-155).

    Temporal semantics: a set is_pr=True when it was a personal record at
    the moment it was logged, not based on the current all-time max.
    """

    def test_new_weight_pr_is_pr_true(self, day_detail_client, db_setup):
        """A set at a strictly new higher weight is is_pr=True (weight PR)."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        today_noon = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

        # Insert a set at a NEW higher weight (120 kg > conftest seed 100 kg).
        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=10, when=today_noon, weight=120.0, reps=5.0,
        )
        try:
            resp = day_detail_client.get(
                f"/api/v1/training/day/{datetime.utcnow().date()}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200, resp.text
            exercises = resp.json()["exercises"]
            sets = next(
                ex["sets"] for ex in exercises
                if ex["exercise_id"] == seed["priv_ex_a"]
            )
            pr_set = next(s for s in sets if s["weight"] == 120.0)
            assert pr_set["is_pr"] is True, (
                f"120 kg > prior max 100 kg must be weight PR: {pr_set}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_lighter_set_is_pr_false(self, day_detail_client, db_setup):
        """A set below the prior max weight (and never lifted) is is_pr=False."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        # Use a future-leaning timestamp so it sorts AFTER the conftest seed rows
        # (which are inserted at NOW() during fixture setup).  The window functions
        # order by (date, set) so "prior" context must include the 100 kg seed rows.
        after_seed = datetime.utcnow() + timedelta(seconds=1)

        # Insert a set at 50 kg while the existing conftest seed has 100 kg as max.
        # 50 kg < 100 kg and 50 kg was never lifted before → not a weight PR,
        # not a reps-at-weight PR (first time at 50 kg, no prior reps to beat).
        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=11, when=after_seed, weight=50.0, reps=10.0,
        )
        try:
            resp = day_detail_client.get(
                f"/api/v1/training/day/{datetime.utcnow().date()}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200, resp.text
            exercises = resp.json()["exercises"]
            sets = next(
                ex["sets"] for ex in exercises
                if ex["exercise_id"] == seed["priv_ex_a"]
            )
            light_set = next(s for s in sets if s["weight"] == 50.0)
            assert light_set["is_pr"] is False, (
                f"Expected is_pr=False for 50 kg set: {light_set}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_first_set_is_pr_second_same_weight_reps_is_not(
        self, day_detail_client, db_setup
    ):
        """Under temporal semantics, a tie (same weight+reps) is NOT a PR.

        Conftest seed inserts set=1 and set=2 at 100 kg x 10 reps for USER_A.
        Set 1 is the first ever set → is_pr=True.
        Set 2 is an exact repeat (same weight AND same reps) → NOT a PR.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        resp = day_detail_client.get(
            f"/api/v1/training/day/{datetime.utcnow().date()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, resp.text
        exercises = resp.json()["exercises"]
        sets = next(
            ex["sets"] for ex in exercises
            if ex["exercise_id"] == seed["priv_ex_a"]
        )
        # Both seed sets are at 100 kg x 10 reps, ordered by set number.
        # Set 1 (first ever) must be is_pr=True; set 2 (tie) must be False.
        assert len(sets) >= 2
        assert sets[0]["is_pr"] is True, (
            f"First set (first ever) must be is_pr=True: {sets[0]}"
        )
        assert sets[1]["is_pr"] is False, (
            f"Second set (same weight+reps, tie) must be is_pr=False: {sets[1]}"
        )

    def test_same_weight_again_on_second_day_is_not_pr(
        self, day_detail_client, db_setup
    ):
        """A repeat at the same weight and reps as a past set is NOT a temporal PR.

        Under the old current-max semantics this returned is_pr=True.
        Under GYM-155 temporal semantics it is not a new record.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        # Insert a heavier set on a past day (150 kg, first time).
        past_day = datetime.utcnow() - timedelta(days=5)
        past_tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=20, when=past_day, weight=150.0, reps=1.0,
        )
        # Insert a today set at the SAME 150 kg x 1 rep = tie, not a new record.
        today_noon = datetime.utcnow().replace(hour=12, minute=2, second=0, microsecond=0)
        today_tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=21, when=today_noon, weight=150.0, reps=1.0,
        )
        try:
            resp = day_detail_client.get(
                f"/api/v1/training/day/{datetime.utcnow().date()}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200, resp.text
            exercises = resp.json()["exercises"]
            sets = next(
                ex["sets"] for ex in exercises
                if ex["exercise_id"] == seed["priv_ex_a"]
            )
            today_set = next(s for s in sets if s["set"] == 21)
            assert today_set["is_pr"] is False, (
                f"Repeat at 150 kg x 1 (tie) must be is_pr=False "
                f"under temporal semantics: {today_set}"
            )
        finally:
            _delete_training_direct(superuser_url, past_tid, today_tid)

    def test_cross_user_pr_isolation(self, day_detail_client, db_setup):
        """User A's history does not affect user B's is_pr computation."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        today = datetime.utcnow().date()

        resp_b = day_detail_client.get(
            f"/api/v1/training/day/{today}",
            headers=_service_headers(USER_B_ID),
        )
        assert resp_b.status_code == 200, resp_b.text
        exercises_b = resp_b.json()["exercises"]
        sets_b = next(
            ex["sets"] for ex in exercises_b
            if ex["exercise_id"] == seed["priv_ex_b"]
        )
        # USER_B's set=1 at 80 kg is their FIRST ever set → is_pr=True.
        # USER_B's set=2 at 80 kg is a repeat → is_pr=False.
        assert len(sets_b) >= 2
        assert sets_b[0]["is_pr"] is True, (
            f"B's first set (first ever) must be is_pr=True: {sets_b[0]}"
        )
        assert sets_b[1]["is_pr"] is False, (
            f"B's second set (repeat) must be is_pr=False: {sets_b[1]}"
        )

    def test_is_pr_field_present_in_response(self, day_detail_client, db_setup):
        """Every set in the response carries the is_pr boolean field."""
        resp = day_detail_client.get(
            f"/api/v1/training/day/{datetime.utcnow().date()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, resp.text
        for ex in resp.json()["exercises"]:
            for s in ex["sets"]:
                assert "is_pr" in s, f"is_pr missing from set: {s}"
                assert isinstance(s["is_pr"], bool), (
                    f"is_pr must be bool, got {type(s['is_pr'])}: {s}"
                )


# ---------------------------------------------------------------------------
# GYM-142 — recency ordering of exercise groups
# ---------------------------------------------------------------------------

class TestRecencyOrder:
    """GET /training/day/{date} returns exercises most-recently-logged first."""

    def test_two_exercises_ordered_by_recency(self, day_detail_client, db_setup):
        """An exercise logged later in the day appears before one logged earlier."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        today = datetime.utcnow().date()

        # Insert two sets for the global exercise at an EARLIER time today.
        earlier = datetime(today.year, today.month, today.day, 8, 0, 0)
        later = datetime(today.year, today.month, today.day, 10, 0, 0)

        global_ex_id = seed["global_ex_id"]
        global_muscle_id = seed["global_muscle_id"]

        tid_early1 = _insert_training(
            superuser_url, USER_A_ID, global_muscle_id, global_ex_id,
            set_num=1, when=earlier, weight=70.0, reps=8.0,
        )
        # priv_ex_a sets are inserted at NOW() in conftest (roughly "now"),
        # but we need a controlled timestamp for the private exercise too.
        # Insert a fresh set for priv_ex_a at LATER timestamp.
        tid_late1 = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=30, when=later, weight=100.0, reps=5.0,
        )
        try:
            resp = day_detail_client.get(
                f"/api/v1/training/day/{today}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200, resp.text
            exercises = resp.json()["exercises"]
            exercise_ids = [ex["exercise_id"] for ex in exercises]

            # priv_ex_a was logged LATER → must appear before global_ex_id.
            idx_priv = exercise_ids.index(seed["priv_ex_a"])
            idx_global = exercise_ids.index(global_ex_id)
            assert idx_priv < idx_global, (
                f"priv_ex_a (later) must precede global_ex_id (earlier). "
                f"Order: {exercise_ids}"
            )
        finally:
            _delete_training_direct(superuser_url, tid_early1, tid_late1)

    def test_sets_within_exercise_still_ascending(self, day_detail_client, db_setup):
        """Sets within each exercise group are still in ascending set-number order."""
        resp = day_detail_client.get(
            f"/api/v1/training/day/{datetime.utcnow().date()}",
            headers=_service_headers(USER_A_ID),
        )
        assert resp.status_code == 200, resp.text
        for ex in resp.json()["exercises"]:
            set_nums = [s["set"] for s in ex["sets"]]
            assert set_nums == sorted(set_nums), (
                f"Sets within exercise '{ex['exercise_name']}' must be ascending: "
                f"{set_nums}"
            )

    def test_single_exercise_day_returns_correctly(self, day_detail_client, db_setup):
        """A day with only one exercise returns that exercise with correct is_pr."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]
        past_day = datetime.utcnow() - timedelta(days=30)
        past_date = past_day.date()

        tid = _insert_training(
            superuser_url, USER_A_ID,
            seed["priv_muscle_a"], seed["priv_ex_a"],
            set_num=1, when=past_day, weight=100.0, reps=5.0,
        )
        try:
            resp = day_detail_client.get(
                f"/api/v1/training/day/{past_date}",
                headers=_service_headers(USER_A_ID),
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert len(data["exercises"]) == 1
            ex = data["exercises"][0]
            assert ex["exercise_id"] == seed["priv_ex_a"]
            assert len(ex["sets"]) == 1
            assert "is_pr" in ex["sets"][0]
        finally:
            _delete_training_direct(superuser_url, tid)
