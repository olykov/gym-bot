"""Integration tests for GYM-153: pr_kind field on TrainingSet.

Validates that GET /training/day/{date} returns the correct pr_kind value
alongside is_pr for every set, and that the invariant

    (pr_kind is None) == (not is_pr)

holds for every set returned by the endpoint.

Scenarios covered:
  - First-ever set of an exercise → pr_kind='weight', is_pr=True
  - Strict weight PR (weight > prior max) → pr_kind='weight', is_pr=True
  - Strict reps-at-weight PR (same weight, more reps) → pr_kind='reps', is_pr=True
  - Non-PR set (repeat weight and reps) → pr_kind=None, is_pr=False
  - Non-PR set (fewer reps at same weight) → pr_kind=None, is_pr=False
  - Invariant check: for all sets on a given day, pr_kind is None iff is_pr False

Reuses the session-scoped ``db_setup`` fixture from conftest (ephemeral
postgres:16) and the helpers from test_gym155_pr_correctness.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import USER_A_ID, _APP_ROLE, _APP_ROLE_PASSWORD
from tests.test_gym155_pr_correctness import (
    _delete_training_direct,
    _ensure_env_defaults,
    _insert_exercise,
    _insert_training,
    _service_headers,
)


# ---------------------------------------------------------------------------
# Module-scoped test client (mirrors pr_client in test_gym155_pr_correctness)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pr_kind_client(db_setup) -> Generator[TestClient, None, None]:
    """Build a TestClient wired to the ephemeral test DB for pr_kind tests.

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
# Helpers
# ---------------------------------------------------------------------------

def _get_sets(
    client: TestClient,
    user_id: int,
    day: str,
    exercise_id: int,
) -> list:
    """Return the sets list for a specific exercise from GET /training/day/{date}.

    Args:
        client: Configured TestClient.
        user_id: User to authenticate as.
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
    for ex in resp.json()["exercises"]:
        if ex["exercise_id"] == exercise_id:
            return ex["sets"]
    return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPrKindWeightVariants:
    """pr_kind='weight' is returned for first-ever sets and strict weight PRs."""

    def test_first_ever_set_pr_kind_weight(self, pr_kind_client, db_setup):
        """The very first set of an exercise has pr_kind='weight' and is_pr=True."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_FirstEver",
        )
        day = (datetime.utcnow() - timedelta(days=70)).date()
        when = datetime(day.year, day.month, day.day, 10, 0, 0)
        tid = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=when, weight=60.0, reps=5.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is True, f"First ever set must be is_pr=True: {s}"
            assert s["pr_kind"] == "weight", (
                f"First ever set must be pr_kind='weight': {s}"
            )
        finally:
            _delete_training_direct(superuser_url, tid)

    def test_strict_weight_pr_kind_weight(self, pr_kind_client, db_setup):
        """A set at a strictly higher weight has pr_kind='weight'."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_WeightPr",
        )
        base = datetime.utcnow() - timedelta(days=65)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=80.0, reps=5.0,
        )
        ts2 = ts1 + timedelta(days=7)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=90.0, reps=5.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is True, f"90 kg > 80 kg must be is_pr=True: {s}"
            assert s["pr_kind"] == "weight", (
                f"Strict weight PR must be pr_kind='weight': {s}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestPrKindReps:
    """pr_kind='reps' is returned for strict reps-at-weight PRs."""

    def test_reps_pr_kind_reps(self, pr_kind_client, db_setup):
        """More reps at same weight than any prior set at that weight → pr_kind='reps'."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_RepsPr",
        )
        base = datetime.utcnow() - timedelta(days=55)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=70.0, reps=5.0,
        )
        ts2 = ts1 + timedelta(days=5)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=70.0, reps=8.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is True, f"8 reps > 5 reps at same weight must be is_pr=True: {s}"
            assert s["pr_kind"] == "reps", (
                f"Reps-at-weight PR must be pr_kind='reps': {s}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_constant_weight_exercise_reps_pr_kind(self, pr_kind_client, db_setup):
        """Bodyweight exercise: the reps record set has pr_kind='reps'."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_Bodyweight",
        )
        base = datetime.utcnow() - timedelta(days=48)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        # First set: 1 kg x 5 → pr_kind='weight' (first ever)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=1.0, reps=5.0,
        )
        # Second set: 1 kg x 10 → pr_kind='reps' (reps record at this weight)
        ts2 = ts1 + timedelta(days=5)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=1.0, reps=10.0,
        )
        try:
            # Verify first set
            sets1 = _get_sets(pr_kind_client, USER_A_ID, str(ts1.date()), eid)
            assert sets1[0]["is_pr"] is True
            assert sets1[0]["pr_kind"] == "weight", (
                f"First ever bodyweight set must be pr_kind='weight': {sets1[0]}"
            )
            # Verify reps record set
            sets2 = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert sets2[0]["is_pr"] is True
            assert sets2[0]["pr_kind"] == "reps", (
                f"Bodyweight reps record must be pr_kind='reps': {sets2[0]}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestPrKindNoneForNonPr:
    """pr_kind=None is returned for all non-PR sets."""

    def test_repeat_set_pr_kind_none(self, pr_kind_client, db_setup):
        """A repeat set (same weight, same reps) has pr_kind=None and is_pr=False."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_RepeatSet",
        )
        base = datetime.utcnow() - timedelta(days=43)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=50.0, reps=8.0,
        )
        ts2 = ts1 + timedelta(days=3)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=50.0, reps=8.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is False, f"Repeat set must be is_pr=False: {s}"
            assert s["pr_kind"] is None, (
                f"Repeat set must be pr_kind=None: {s}"
            )
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_fewer_reps_set_pr_kind_none(self, pr_kind_client, db_setup):
        """Fewer reps at same weight has pr_kind=None."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_FewerReps",
        )
        base = datetime.utcnow() - timedelta(days=38)
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
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is False, f"Fewer reps set must be is_pr=False: {s}"
            assert s["pr_kind"] is None, f"Fewer reps set must be pr_kind=None: {s}"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_lower_weight_not_pr_kind_none(self, pr_kind_client, db_setup):
        """A set at a weight below the prior max has pr_kind=None (not a weight PR)."""
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_LowerWeight",
        )
        base = datetime.utcnow() - timedelta(days=35)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=100.0, reps=3.0,
        )
        ts2 = ts1 + timedelta(days=4)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=70.0, reps=8.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]
            assert s["is_pr"] is False, f"Lower weight must be is_pr=False: {s}"
            assert s["pr_kind"] is None, f"Lower weight must be pr_kind=None: {s}"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)


class TestPrKindInvariant:
    """Invariant: (pr_kind is None) == (not is_pr) for every set on a day."""

    def test_invariant_mixed_day(self, pr_kind_client, db_setup):
        """On a day with both PR and non-PR sets, invariant holds for every set.

        Inserts a first-ever set (pr_kind='weight', is_pr=True) and a second
        repeat set (pr_kind=None, is_pr=False) on the same day, then checks
        the invariant holds for both.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_InvariantMixed",
        )
        day = (datetime.utcnow() - timedelta(days=30)).date()
        ts1 = datetime(day.year, day.month, day.day, 10, 0, 0)
        ts2 = datetime(day.year, day.month, day.day, 10, 5, 0)
        # Set 1: first ever — is_pr=True, pr_kind='weight'
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=60.0, reps=5.0,
        )
        # Set 2: repeat — is_pr=False, pr_kind=None
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=2, when=ts2, weight=60.0, reps=5.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day), eid)
            assert len(sets) == 2, f"Expected 2 sets, got: {sets}"

            for s in sets:
                # Invariant: pr_kind is None iff is_pr is False
                pr_kind_is_none = s["pr_kind"] is None
                is_not_pr = not s["is_pr"]
                assert pr_kind_is_none == is_not_pr, (
                    f"Invariant violated for set {s}: "
                    f"pr_kind={s['pr_kind']!r}, is_pr={s['is_pr']}"
                )

            # Also assert the specific values.
            assert sets[0]["pr_kind"] == "weight", f"Set 1 must be pr_kind='weight': {sets[0]}"
            assert sets[1]["pr_kind"] is None, f"Set 2 must be pr_kind=None: {sets[1]}"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)

    def test_invariant_reps_pr_day(self, pr_kind_client, db_setup):
        """On a day with a reps-PR set, invariant still holds for that set.

        History: prior set at 50 kg x 5 reps, then today 50 kg x 10 reps.
        Today's set must have pr_kind='reps' and is_pr=True.
        """
        superuser_url = db_setup["superuser_url"]
        seed = db_setup["seed"]

        eid = _insert_exercise(
            superuser_url, USER_A_ID, seed["priv_muscle_a"],
            "GYM153_InvariantReps",
        )
        base = datetime.utcnow() - timedelta(days=25)
        ts1 = base.replace(hour=12, minute=0, second=0, microsecond=0)
        tid1 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts1, weight=50.0, reps=5.0,
        )
        ts2 = ts1 + timedelta(days=5)
        day2 = ts2.date()
        tid2 = _insert_training(
            superuser_url, USER_A_ID, seed["priv_muscle_a"], eid,
            set_num=1, when=ts2, weight=50.0, reps=10.0,
        )
        try:
            sets = _get_sets(pr_kind_client, USER_A_ID, str(day2), eid)
            assert len(sets) == 1
            s = sets[0]

            # Invariant check
            pr_kind_is_none = s["pr_kind"] is None
            is_not_pr = not s["is_pr"]
            assert pr_kind_is_none == is_not_pr, (
                f"Invariant violated: pr_kind={s['pr_kind']!r}, is_pr={s['is_pr']}"
            )

            # Specific assertion
            assert s["is_pr"] is True
            assert s["pr_kind"] == "reps"
        finally:
            _delete_training_direct(superuser_url, tid1, tid2)
