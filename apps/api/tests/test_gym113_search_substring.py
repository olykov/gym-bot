"""GYM-113: Regression tests for substring (contains) matching in exercise search.

Problem: a query that is a word in the MIDDLE or END of an exercise name did not
prefix-match, so only a weak fuzzy hit was returned (or none).  Example: 'Press'
matches 'Barbell Bench Press' and 'Cable Chest Press' but neither starts with
'Press', so the old prefix-only tier missed both.

Fix: added a CONTAINS tier (tier 3) on ``exercises.name_key`` with
``name_key LIKE '%' || q || '%'``, score 0.5, match_reason='prefix' (same silent
UX badge; no new enum value; contract unchanged).  Also extended the alias tier
from prefix-match to substring-match on ``exercise_alias.name_key``.

Covers:
  1. 'Press' (muscle-scoped) returns ALL exercises containing 'Press',
     not just one fuzzy hit — core regression.
  2. Substring in the middle of the name is found (not only at the end).
  3. Exact match still outranks contains match for the same exercise.
  4. Prefix match still outranks contains match (score ordering within 'prefix' bucket).
  5. Alias tier: a substring of an alias name resolves the exercise.
  6. Muscle scoping is respected for contains hits.
  7. A query that matches nothing still returns [].
  8. RLS isolation: another user's private exercise is not returned via contains.

Seed (USER_113_ID = 500113, USER_113B_ID = 500114):
  global_muscle_113:  global muscle for all test exercises.
  ex_barbell_press:   'Gym113 Barbell Bench Press' — contains 'press' at the end.
  ex_cable_press:     'Gym113 Cable Chest Press' — contains 'press' at the end.
  ex_dumbbell_press:  'Gym113 Dumbbell Bench Press' — contains 'press' at the end.
  ex_press_start:     'Gym113 Press Up' — starts with 'press' (prefix tier).
  ex_bench_middle:    'Gym113 Flat Bench Fly' — contains 'bench' in the middle.
  ex_alias_press:     'Gym113 Squat' with alias 'Gym113 Leg Press Variant'.
  private_ex_b:       private exercise for USER_113B_ID (must NOT be seen by A).
"""

import os
import sys
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_113_ID = 500113
USER_113B_ID = 500114

_MUSCLE_NAME = "Gym113 Global Muscle"
_BARBELL_PRESS = "Gym113 Barbell Bench Press"
_CABLE_PRESS = "Gym113 Cable Chest Press"
_DUMBBELL_PRESS = "Gym113 Dumbbell Bench Press"
# 'Press Machine' normalizes to 'press machine' — starts with 'press', so prefix-match.
_PRESS_START = "Press Machine Gym113"
_BENCH_MIDDLE = "Gym113 Flat Bench Fly"
_SQUAT = "Gym113 Squat"
_ALIAS_PRESS = "Gym113 Leg Press Variant"
_PRIVATE_B = "Gym113 Private B Exercise"


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
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_gym113(superuser_url: str) -> dict:
    """Insert seed data for GYM-113 substring-search regression tests.

    Creates a global muscle and several exercises whose names contain 'press'
    at various positions, plus an exercise with an alias containing 'press',
    to validate all paths of the new contains tier.

    Args:
        superuser_url: Superuser connection URL.

    Returns:
        Dict with exercise and muscle ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        # Users
        for uid, first_name, username in [
            (USER_113_ID, "User113A", "user113a_test"),
            (USER_113B_ID, "User113B", "user113b_test"),
        ]:
            conn.execute(text("""
                INSERT INTO users (id, registration_date, first_name, username)
                VALUES (:uid, NOW(), :fn, :un)
                ON CONFLICT (id) DO NOTHING
            """), {"uid": uid, "fn": first_name, "un": username})

        # Global muscle
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES (:name, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"name": _MUSCLE_NAME})
        muscle_id = conn.execute(text(
            "SELECT id FROM muscles WHERE name = :name AND created_by IS NULL"
        ), {"name": _MUSCLE_NAME}).scalar_one()

        # Global exercises
        ids: dict = {}
        for ex_name in [
            _BARBELL_PRESS,
            _CABLE_PRESS,
            _DUMBBELL_PRESS,
            _PRESS_START,
            _BENCH_MIDDLE,
            _SQUAT,
        ]:
            conn.execute(text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, TRUE, NULL)
                ON CONFLICT DO NOTHING
            """), {"name": ex_name, "mid": muscle_id})
            ids[ex_name] = conn.execute(text(
                "SELECT id FROM exercises WHERE name = :name AND created_by IS NULL"
            ), {"name": ex_name}).scalar_one()

        # Alias for _SQUAT: 'Gym113 Leg Press Variant' — contains 'press'
        conn.execute(text("""
            INSERT INTO exercise_alias (canonical_id, alias_name, lang, is_global, created_by)
            VALUES (:cid, :alias, 'en', TRUE, NULL)
            ON CONFLICT (canonical_id, name_key) DO NOTHING
        """), {"cid": ids[_SQUAT], "alias": _ALIAS_PRESS})

        # Private exercise for USER_113B_ID (must not appear for A)
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES (:name, :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"name": _PRIVATE_B, "mid": muscle_id, "uid": USER_113B_ID})
        priv_b_id = conn.execute(text(
            "SELECT id FROM exercises WHERE name = :name AND created_by = :uid"
        ), {"name": _PRIVATE_B, "uid": USER_113B_ID}).scalar_one()

        conn.commit()
    eng.dispose()

    return {
        "muscle_id": muscle_id,
        "ex_barbell_press": ids[_BARBELL_PRESS],
        "ex_cable_press": ids[_CABLE_PRESS],
        "ex_dumbbell_press": ids[_DUMBBELL_PRESS],
        "ex_press_start": ids[_PRESS_START],
        "ex_bench_middle": ids[_BENCH_MIDDLE],
        "ex_squat": ids[_SQUAT],
        "private_ex_b": priv_b_id,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient + seed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym113_client(db_setup) -> Generator:
    """Build a TestClient for GYM-113 tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym113(db_setup["superuser_url"])

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
    yield client, seed

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSubstringMatchCoreRegression:
    """Core GYM-113 regression: 'Press' must return all exercises containing 'press'."""

    def test_press_query_returns_all_press_exercises(self, gym113_client):
        """'Press' (muscle-scoped) returns all exercises whose name contains 'press'.

        Before GYM-113: only one fuzzy hit was returned.  After GYM-113: all
        three exercises whose names end in '...Bench Press' / '...Chest Press'
        are returned via the new contains tier.
        """
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "press", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        returned_ids = {it["id"] for it in items}

        # All three end-word 'press' exercises must be found.
        assert seed["ex_barbell_press"] in returned_ids, (
            f"Gym113 Barbell Bench Press not in results: {[it['name'] for it in items]}"
        )
        assert seed["ex_cable_press"] in returned_ids, (
            f"Gym113 Cable Chest Press not in results: {[it['name'] for it in items]}"
        )
        assert seed["ex_dumbbell_press"] in returned_ids, (
            f"Gym113 Dumbbell Bench Press not in results: {[it['name'] for it in items]}"
        )

    def test_press_contains_results_have_prefix_reason(self, gym113_client):
        """Contains hits on name_key are returned with match_reason='prefix'.

        The contract enum is exact|prefix|alias|fuzzy.  The contains tier
        emits 'prefix' so no new value is needed (GYM-113 design decision).
        """
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "press", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        contains_ids = {
            seed["ex_barbell_press"],
            seed["ex_cable_press"],
            seed["ex_dumbbell_press"],
        }
        for it in items:
            if it["id"] in contains_ids:
                assert it["match_reason"] == "prefix", (
                    f"Contains hit {it['name']!r} should have match_reason='prefix'; "
                    f"got {it['match_reason']!r}"
                )


class TestSubstringInTheMiddle:
    """A query that is a word in the middle of the name is found."""

    def test_bench_in_middle_found(self, gym113_client):
        """'bench' (middle of 'Gym113 Flat Bench Fly') is matched by contains tier."""
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "bench", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        returned_ids = {it["id"] for it in items}
        assert seed["ex_bench_middle"] in returned_ids, (
            f"Gym113 Flat Bench Fly (contains 'bench' in middle) not found; "
            f"results: {[it['name'] for it in items]}"
        )
        # Also verify reason
        for it in items:
            if it["id"] == seed["ex_bench_middle"]:
                assert it["match_reason"] == "prefix", (
                    f"Expected match_reason='prefix' for contains hit; "
                    f"got {it['match_reason']!r}"
                )


class TestTierOrdering:
    """Exact and prefix tiers still outrank the contains tier for the same exercise."""

    def test_prefix_hit_outranks_contains_hit(self, gym113_client):
        """'Press Up' starts with 'press', so it prefix-matches and ranks above contains hits.

        'Gym113 Press Up' prefix-matches 'press' (score 0.8).
        'Gym113 Barbell Bench Press' etc. contain-match 'press' (score 0.5).
        The prefix hit must appear before the contains hits in the result list.
        """
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "press", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert items, "Expected at least one result"

        ids_in_order = [it["id"] for it in items]
        prefix_pos = next(
            (i for i, it in enumerate(items) if it["id"] == seed["ex_press_start"]),
            None,
        )
        contains_positions = [
            i for i, it in enumerate(items)
            if it["id"] in {
                seed["ex_barbell_press"],
                seed["ex_cable_press"],
                seed["ex_dumbbell_press"],
            }
        ]
        assert prefix_pos is not None, (
            f"'Gym113 Press Up' (prefix match) not found in results; ids: {ids_in_order}"
        )
        assert contains_positions, "No contains hits found"
        assert all(prefix_pos < cp for cp in contains_positions), (
            f"Prefix hit (pos {prefix_pos}) must come before all contains hits "
            f"(positions {contains_positions})"
        )

    def test_exact_hit_outranks_everything(self, gym113_client):
        """Exact match on 'Gym113 Barbell Bench Press' ranks first when queried exactly."""
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={
                "q": "Gym113 Barbell Bench Press",
                "muscle_id": seed["muscle_id"],
                "limit": 20,
            },
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert items, "Expected at least one result"
        best = items[0]
        assert best["id"] == seed["ex_barbell_press"], (
            f"Exact match should rank first; got {best['name']!r}"
        )
        assert best["match_reason"] == "exact", (
            f"Expected match_reason='exact'; got {best['match_reason']!r}"
        )
        assert best["score"] == pytest.approx(1.0)


class TestAliasSubstringExtension:
    """GYM-113: the alias tier now uses LIKE '%'||q||'%' (was exact/prefix only)."""

    def test_substring_of_alias_resolves_exercise(self, gym113_client):
        """A query that is a substring of an alias name resolves the exercise.

        'Gym113 Leg Press Variant' is an alias for 'Gym113 Squat'.  Querying
        'leg press' (substring of the alias) must return the squat exercise.
        """
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "leg press", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        hit_ids = {it["id"] for it in alias_hits}
        assert seed["ex_squat"] in hit_ids, (
            f"Gym113 Squat (aliased via 'Gym113 Leg Press Variant') not found "
            f"via alias tier; alias_hits: {alias_hits}; all items: {items}"
        )


class TestMuscleFilterWithContains:
    """Muscle scoping is preserved for the new contains tier."""

    def test_contains_hit_respects_muscle_filter(self, gym113_client, db_setup):
        """Contains hits are confined to the specified muscle_id."""
        client, seed = gym113_client

        # Insert an exercise with 'press' in a different muscle.
        eng = create_engine(db_setup["superuser_url"], poolclass=NullPool)
        with eng.connect() as conn:
            conn.execute(text("""
                INSERT INTO muscles (name, is_global, created_by)
                VALUES ('Gym113 Other Muscle', TRUE, NULL)
                ON CONFLICT DO NOTHING
            """))
            other_mid = conn.execute(text(
                "SELECT id FROM muscles "
                "WHERE name = 'Gym113 Other Muscle' AND created_by IS NULL"
            )).scalar_one()
            conn.execute(text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES ('Gym113 Other Shoulder Press', :mid, TRUE, NULL)
                ON CONFLICT DO NOTHING
            """), {"mid": other_mid})
            conn.commit()
        eng.dispose()

        # Scoped to gym113_muscle: 'Gym113 Other Shoulder Press' must NOT appear.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "press", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        returned_muscles = {it["muscle"] for it in items}
        assert returned_muscles <= {seed["muscle_id"]}, (
            f"Expected only muscle {seed['muscle_id']}; got {returned_muscles}"
        )


class TestNoMatchAndIsolation:
    """Empty results and RLS isolation."""

    def test_no_match_returns_empty(self, gym113_client):
        """A query with no substring/prefix/fuzzy match returns []."""
        client, seed = gym113_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "xqzxqz_gym113_nomatch", "muscle_id": seed["muscle_id"]},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_other_user_private_not_returned_via_contains(self, gym113_client):
        """Another user's private exercise is not returned even via contains tier (RLS)."""
        client, seed = gym113_client
        # _PRIVATE_B = 'Gym113 Private B Exercise'; query 'private b' to force contains.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "private b", "muscle_id": seed["muscle_id"], "limit": 20},
            headers=_service_headers(USER_113_ID),
        )
        assert resp.status_code == 200, resp.text
        returned_ids = {it["id"] for it in resp.json()}
        assert seed["private_ex_b"] not in returned_ids, (
            "Another user's private exercise must not appear via contains tier"
        )
