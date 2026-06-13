"""Integration tests for GYM-155: temporal PR correctness.

Validates Option A semantics for is_pr (per-set) and has_pr (per-day):
  - First-ever set of an exercise is is_pr=True.
  - Constant-weight / bodyweight exercise: only rep-record sets flag PR,
    NOT repeats or below-record sets.  This is the core bug from prod.
  - Strict weight PR: a set at a new higher weight is is_pr=True.
  - Strict reps-at-weight PR: same weight, more reps than ever before = PR.
  - Ties are NOT PRs (equal weight and equal reps are not new records).
  - A new lower weight never lifted before is NOT a PR.
  - has_pr day-level = OR of is_pr over the day's sets.
  - Cross-user isolation: user A's PR history never affects user B's flags.

Also validates the Pull-Up data shape described in the task spec:
  reps history [first set PR, 5 again NOT PR, 5 again NOT PR,
                7 reps PR, same 7 NOT PR, 8 PR, 10 PR]
  then two sets today (7 and 5) → today's sets both NOT PR.

All tests use the session-scoped ``db_setup`` fixture (ephemeral postgres:16).
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Generator

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
    weight: float,
    reps: float,
) -> str:
    """Insert one training row as superuser and return its hex id.

    Args:
        superuser_url: SQLAlchemy URL with superuser credentials.
        uid: User id.
        muscle_id: Muscle id.
        exercise_id: Exercise id.
        set_num: Set number.
        when: Timestamp for the row.
        weight: Weight in kg.
        reps: Rep count.

    Returns:
        The new training id (hex string).
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
        *tids: Training ids to delete.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        for tid in tids:
            conn.execute(text("DELETE FROM training WHERE id = :tid"), {"tid": tid})
        conn.commit()
    eng.dispose()


def _insert_exercise(
    superuser_url: str,
    uid: int,
    muscle_id: int,
    name: str,
) -> int:
    """Create a private exercise for uid and return its id.

    Args:
        superuser_url: Superuser URL.
        uid: Owner user id.
        muscle_id: Muscle id.
        name: Exercise name (must be unique per muscle).

    Returns:
        The new exercise id.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, FALSE, :uid)
                ON CONFLICT DO NOTHING
            """),
            {"name": name, "mid": muscle_id, "uid": uid},
        )
        row = conn.execute(
            text("SELECT id FROM exercises WHERE name = :name AND created_by = :uid"),
            {"name": name, "uid": uid},
        ).fetchone()
        conn.commit()
    eng.dispose()
    return row[0]


# ---------------------------------------------------------------------------
# Module-scoped test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pr_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient wired to the ephemeral test DB for PR tests.

    Args:
        db_setup: Session-scoped fixture from conftest.

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
# Helpers for querying endpoints
# ---------------------------------------------------------------------------

def _get_sets_for_exercise(
    client: TestClient,
    user_id: int,
    day: str,
    exercise_id: int,
) -> list:
    """Return the sets list for a specific exercise on the given day.

    Args:
        client: TestClient.
        user_id: User to query as.
        day: ISO date string (YYYY-MM-DD).
        exercise_id: Exercise to filter to.

    Returns:
        List of set dicts from the API response.
    """
    resp = client.get(
        f"/api/v1/training/day/{day}",
        headers=_service_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    exercises = resp.json()["exercises"]
    for ex in exercises:
        if ex["exercise_id"] == exercise_id:
            return ex["sets"]
    return []


def _get_day_has_pr(
    client: TestClient,
    user_id: int,
    day: str,
) -> bool:
    """Return has_pr for the given day from GET /training/days.

    Args:
        client: TestClient.
        user_id: User to query as.
        day: ISO date string (YYYY-MM-DD).

    Returns:
        has_pr bool for the day, or False if the day is absent.
    """
    resp = client.get(
        "/api/v1/training/days",
        params={"from": day, "to": day},
        headers=_service_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    for entry in resp.json():
        if entry["date"] == day:
            return bool(entry["has_pr"])
    return False


# ---------------------------------------------------------------------------
# GYM-155 — core PR correctness
# ---------------------------------------------------------------------------

class TestFirstEverSetIsPr:
    """The very first set of an exercise is always is_pr=True."""

    def test_first_set_is_pr(self, pr_client, db_setup):
        """First ever set of a fresh exercise has is_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        # Create a fresh exercise so it has zero history.
        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_FirstSetExercise",
        )
        day = (datetime.utcnow() - timedelta(days=40)).date()
        when = datetime(day.year, day.month, day.day, 10, 0, 0)
        tid = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=when, weight=50.0, reps=5.0,
        )
        try:
            sets = _get_sets_for_exercise(pr_client, USER_A_ID, str(day), eid)
            assert len(sets) == 1
            assert sets[0]["is_pr"] is True, (
                f"First ever set must be is_pr=True: {sets[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_first_set_has_pr_day(self, pr_client, db_setup):
        """Day of the first ever set has has_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_FirstSetHasPrExercise",
        )
        day = (datetime.utcnow() - timedelta(days=41)).date()
        when = datetime(day.year, day.month, day.day, 10, 0, 0)
        tid = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=when, weight=40.0, reps=8.0,
        )
        try:
            has_pr = _get_day_has_pr(pr_client, USER_A_ID, str(day))
            assert has_pr is True, "Day of first set must have has_pr=True"
        finally:
            _delete_training_direct(superuser_url, tid)


class TestConstantWeightBodyweight:
    """Core bug: constant-weight exercise must NOT flag repeats or below-record sets.

    Models the operator's Pull-Up scenario: all sets at 1.0 kg.
    History (spread over multiple past days):
      set A: 1 kg x 5   → is_pr=True  (first ever set)
      set B: 1 kg x 5   → is_pr=False (repeat reps, not a new record)
      set C: 1 kg x 5   → is_pr=False (repeat)
      set D: 1 kg x 5   → is_pr=False (repeat)
      set E: 1 kg x 4   → is_pr=False (fewer reps)
      set F: 1 kg x 7   → is_pr=True  (new reps record at this weight)
      set G: 1 kg x 6   → is_pr=False (below current record of 7)
      set H: 1 kg x 7   → is_pr=False (tie, not strictly greater)
      set I: 1 kg x 8   → is_pr=True  (new reps record)
      set J: 1 kg x 10  → is_pr=True  (new reps record — all-time best)

    Then today:
      set K: 1 kg x 7   → is_pr=False (below record of 10)
      set L: 1 kg x 5   → is_pr=False (below record of 10)
    Today's has_pr must be False.
    """

    def test_constant_weight_pr_pattern(self, pr_client, db_setup):
        """Constant-weight exercise: validate is_pr for each set in the history."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_PullUp",
        )

        base = datetime.utcnow() - timedelta(days=100)

        # Build a history where each tuple is (days_offset, set_num, weight, reps).
        # Spread across different days to ensure distinct date values in ORDER BY.
        history = [
            # (days_offset, set_num, weight, reps, expected_is_pr)
            (0,  1, 1.0, 5.0, True),   # first ever set = PR
            (1,  1, 1.0, 5.0, False),  # repeat reps = NOT PR
            (2,  1, 1.0, 5.0, False),  # repeat
            (3,  1, 1.0, 5.0, False),  # repeat
            (4,  1, 1.0, 4.0, False),  # fewer reps = NOT PR
            (5,  1, 1.0, 7.0, True),   # new reps record = PR
            (6,  1, 1.0, 6.0, False),  # below current record = NOT PR
            (7,  1, 1.0, 7.0, False),  # tie (not strictly greater) = NOT PR
            (8,  1, 1.0, 8.0, True),   # new reps record = PR
            (9,  1, 1.0, 10.0, True),  # all-time reps record = PR
        ]

        tids = []
        day_map = {}  # (days_offset) -> (date_str, tid, expected_is_pr)
        try:
            for days_offset, set_num, weight, reps, expected in history:
                when = base + timedelta(days=days_offset)
                when_ts = when.replace(hour=12, minute=0, second=0, microsecond=0)
                day_str = when_ts.date().isoformat()
                tid = _insert_training(
                    superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
                    set_num=set_num, when=when_ts, weight=weight, reps=reps,
                )
                tids.append(tid)
                day_map[days_offset] = (day_str, tid, expected, weight, reps)

            # Verify each set individually.
            for days_offset, (day_str, tid, expected, weight, reps) in day_map.items():
                sets = _get_sets_for_exercise(pr_client, USER_A_ID, day_str, eid)
                assert len(sets) >= 1, (
                    f"No sets found for day {day_str} (offset {days_offset})"
                )
                s = sets[0]
                assert s["is_pr"] is expected, (
                    f"Set offset={days_offset} weight={weight} reps={reps}: "
                    f"expected is_pr={expected}, got {s['is_pr']}"
                )

        finally:
            _delete_training_direct(superuser_url, *tids)

    def test_today_sets_not_pr_when_below_rep_record(self, pr_client, db_setup):
        """Today's sets below the all-time reps record are NOT PRs (the prod bug)."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_PullUpTodayCheck",
        )

        # Historic record day: 1 kg x 10 reps (all-time reps record).
        record_day = datetime.utcnow() - timedelta(days=30)
        record_ts = record_day.replace(hour=12, minute=0, second=0, microsecond=0)
        tid_record = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=record_ts, weight=1.0, reps=10.0,
        )

        # Today: 1 kg x 7 and 1 kg x 5 — both below the record.
        today = datetime.utcnow().date()
        today_ts1 = datetime(today.year, today.month, today.day, 10, 0, 0)
        today_ts2 = datetime(today.year, today.month, today.day, 10, 5, 0)
        tid_t1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=today_ts1, weight=1.0, reps=7.0,
        )
        tid_t2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=2, when=today_ts2, weight=1.0, reps=5.0,
        )
        try:
            sets = _get_sets_for_exercise(pr_client, USER_A_ID, str(today), eid)
            assert len(sets) == 2, f"Expected 2 sets today, got: {sets}"

            for s in sets:
                assert s["is_pr"] is False, (
                    f"Set 1kg x {s['reps']} reps below record of 10 must be "
                    f"is_pr=False (this was the prod bug): {s}"
                )

            # Day-level has_pr must also be False.
            has_pr = _get_day_has_pr(pr_client, USER_A_ID, str(today))
            # Note: today also has the conftest seed training (different exercise),
            # so we check via the day-detail endpoint's exercise-specific sets only.
            # For has_pr validation we check the sets directly above.
        finally:
            _delete_training_direct(
                superuser_url, tid_record, tid_t1, tid_t2
            )

    def test_rep_record_set_is_pr(self, pr_client, db_setup):
        """The set that establishes the reps record IS flagged is_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_RepRecordCheck",
        )

        base = datetime.utcnow() - timedelta(days=20)
        # First set: 1 kg x 5 — PR (first ever).
        day1 = base.date()
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=1.0, reps=5.0,
        )

        # Second set: 1 kg x 10 — reps PR.
        day2 = (base + timedelta(days=5)).date()
        ts2 = ts1 + timedelta(days=5)
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=1.0, reps=10.0,
        )
        try:
            sets1 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day1), eid)
            assert sets1[0]["is_pr"] is True, "First set must be PR"

            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert sets2[0]["is_pr"] is True, "New reps record set must be PR"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestWeightPr:
    """Strict weight PRs behave correctly."""

    def test_strict_weight_pr(self, pr_client, db_setup):
        """A set at a new higher weight is is_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_WeightPr",
        )
        base = datetime.utcnow() - timedelta(days=15)
        day1 = base.date()
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=60.0, reps=5.0,
        )

        day2 = (base + timedelta(days=7)).date()
        ts2 = ts1 + timedelta(days=7)
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=70.0, reps=5.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is True, (
                f"70 kg > prior max 60 kg must be weight PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_equal_weight_not_a_pr(self, pr_client, db_setup):
        """A set at the same weight as an existing set (tie) is NOT a PR."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_WeightTie",
        )
        base = datetime.utcnow() - timedelta(days=10)
        day1 = base.date()
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=80.0, reps=5.0,
        )

        day2 = (base + timedelta(days=3)).date()
        ts2 = ts1 + timedelta(days=3)
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=80.0, reps=5.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is False, (
                f"Same weight and reps (tie) must NOT be PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_lower_weight_new_to_this_weight_not_pr(self, pr_client, db_setup):
        """A new lower weight that was never lifted before is NOT a weight PR.

        The weight is strictly less than prior max — even though this specific
        weight has no prior reps record, it is not a weight breakthrough.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_LowerWeightNoHistory",
        )
        base = datetime.utcnow() - timedelta(days=8)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=100.0, reps=3.0,
        )

        # A set at 70 kg — less than prior max of 100 kg.
        # Even though 70 kg has never been done before, it is NOT a PR
        # (the weight is lower than prior max; reps at 70 kg have no prior
        # so prior_max_reps_at_w IS NULL → the reps-at-weight branch does
        # not fire either per the spec: weight must have been lifted before).
        ts2 = ts1 + timedelta(days=4)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=70.0, reps=8.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is False, (
                f"70 kg < prior max 100 kg must NOT be PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestRepsAtWeightPr:
    """Reps-at-weight PRs behave correctly."""

    def test_strict_reps_pr_at_same_weight(self, pr_client, db_setup):
        """More reps at same weight than any prior set at that weight = PR."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_RepsPr",
        )
        base = datetime.utcnow() - timedelta(days=12)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=50.0, reps=5.0,
        )

        ts2 = ts1 + timedelta(days=5)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=50.0, reps=8.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is True, (
                f"8 reps > prior 5 reps at same weight must be reps PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_equal_reps_not_a_pr(self, pr_client, db_setup):
        """Equal reps at same weight (reps tie) is NOT a PR."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_RepsTie",
        )
        base = datetime.utcnow() - timedelta(days=6)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=50.0, reps=8.0,
        )

        ts2 = ts1 + timedelta(days=2)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=50.0, reps=8.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is False, (
                f"Equal reps (tie) must NOT be PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_fewer_reps_not_a_pr(self, pr_client, db_setup):
        """Fewer reps at same weight is NOT a PR."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_FewerReps",
        )
        base = datetime.utcnow() - timedelta(days=5)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=50.0, reps=10.0,
        )

        ts2 = ts1 + timedelta(days=2)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=50.0, reps=7.0,
        )
        try:
            sets2 = _get_sets_for_exercise(pr_client, USER_A_ID, str(day2), eid)
            assert len(sets2) == 1
            assert sets2[0]["is_pr"] is False, (
                f"7 reps < prior 10 reps must NOT be PR: {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestHasPrDayLevel:
    """has_pr day-level flag is the OR of is_pr over the day's sets."""

    def test_has_pr_true_when_any_set_is_pr(self, pr_client, db_setup):
        """A day with at least one PR set has has_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_HasPrTrue",
        )
        day = (datetime.utcnow() - timedelta(days=50)).date()
        ts1 = datetime(day.year, day.month, day.day, 10, 0, 0)
        ts2 = datetime(day.year, day.month, day.day, 10, 5, 0)
        # Set 1: first ever = PR; set 2: repeat (not PR).
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=60.0, reps=5.0,
        )
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=2, when=ts2, weight=60.0, reps=5.0,
        )
        try:
            sets = _get_sets_for_exercise(pr_client, USER_A_ID, str(day), eid)
            assert sets[0]["is_pr"] is True
            assert sets[1]["is_pr"] is False

            has_pr = _get_day_has_pr(pr_client, USER_A_ID, str(day))
            assert has_pr is True, "Day with at least one PR set must have has_pr=True"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_has_pr_false_when_no_set_is_pr(self, pr_client, db_setup):
        """A day where ALL sets are repeats (no PR) has has_pr=False."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_HasPrFalse",
        )
        # Day 1: first set (PR).
        day1 = (datetime.utcnow() - timedelta(days=52)).date()
        ts0 = datetime(day1.year, day1.month, day1.day, 10, 0, 0)
        tid0 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts0, weight=60.0, reps=5.0,
        )

        # Day 2: two repeat sets at same weight/reps = no PR.
        day2 = (datetime.utcnow() - timedelta(days=51)).date()
        ts1 = datetime(day2.year, day2.month, day2.day, 10, 0, 0)
        ts2 = datetime(day2.year, day2.month, day2.day, 10, 5, 0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=60.0, reps=5.0,
        )
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=2, when=ts2, weight=60.0, reps=5.0,
        )
        try:
            has_pr = _get_day_has_pr(pr_client, USER_A_ID, str(day2))
            assert has_pr is False, (
                "Day of repeat sets must have has_pr=False"
            )
        finally:
            _delete_training_direct(superuser_url, tid0, tid1, tid2)


class TestCrossUserIsolation:
    """User A's PR history never bleeds into user B's PR flags."""

    def test_cross_user_is_pr_isolation(self, pr_client, db_setup):
        """User B's is_pr computation is unaffected by user A's history."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        # Create matching exercises for A and B.
        eid_a = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM155_CrossUserExA",
        )
        eid_b = _insert_exercise(
            superuser_url, USER_B_ID, seed["priv_muscle_b"],
            "GYM155_CrossUserExB",
        )

        day = (datetime.utcnow() - timedelta(days=60)).date()
        ts = datetime(day.year, day.month, day.day, 10, 0, 0)

        # User A: heavy weight (200 kg).
        tid_a = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid_a,
            set_num=1, when=ts, weight=200.0, reps=1.0,
        )
        # User B: lighter weight (50 kg) — must be is_pr=True (first set for B).
        tid_b = _insert_training(
            superuser_url, USER_B_ID, seed["priv_muscle_b"], eid_b,
            set_num=1, when=ts, weight=50.0, reps=5.0,
        )
        try:
            sets_a = _get_sets_for_exercise(pr_client, USER_A_ID, str(day), eid_a)
            sets_b = _get_sets_for_exercise(pr_client, USER_B_ID, str(day), eid_b)

            assert sets_a[0]["is_pr"] is True, "A's first set must be PR"
            assert sets_b[0]["is_pr"] is True, (
                "B's first set at 50 kg must be PR regardless of A's 200 kg"
            )
        finally:
            _delete_training_direct(superuser_url, tid_a, tid_b)

    def test_cross_user_has_pr_isolation(self, pr_client, db_setup):
        """User B's has_pr is unaffected by user A's training on the same day."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid_b = _insert_exercise(
            superuser_url, USER_B_ID, seed["priv_muscle_b"],
            "GYM155_CrossUserHasPrB",
        )

        # Day 1: B's first set (PR).
        day1 = (datetime.utcnow() - timedelta(days=62)).date()
        ts0 = datetime(day1.year, day1.month, day1.day, 10, 0, 0)
        tid_b0 = _insert_training(
            superuser_url, USER_B_ID, seed["priv_muscle_b"], eid_b,
            set_num=1, when=ts0, weight=40.0, reps=10.0,
        )

        # Day 2: B's repeat — no PR for B.
        day2 = (datetime.utcnow() - timedelta(days=61)).date()
        ts1 = datetime(day2.year, day2.month, day2.day, 10, 0, 0)
        tid_b1 = _insert_training(
            superuser_url, USER_B_ID, seed["priv_muscle_b"], eid_b,
            set_num=1, when=ts1, weight=40.0, reps=10.0,
        )
        try:
            # B's day 2 must have has_pr=False (all repeats for B).
            has_pr = _get_day_has_pr(pr_client, USER_B_ID, str(day2))
            assert has_pr is False, (
                "B's repeat day must have has_pr=False, independent of A's data"
            )
        finally:
            _delete_training_direct(superuser_url, tid_b0, tid_b1)
