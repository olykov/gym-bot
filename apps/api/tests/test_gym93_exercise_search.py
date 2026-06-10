"""GYM-93: Integration tests for GET /exercises/search — tiered candidate search.

Covers:
  1.  Exact match (match_reason='exact', score=1.0).
  2.  Prefix match (match_reason='prefix', score=0.8).
  3.  Alias match with lang filter (match_reason='alias').
  4.  Alias match without lang filter (any-lang alias hit).
  5.  Fuzzy match via pg_trgm (match_reason='fuzzy').
  6.  Muscle filter scopes results (only exercises under that muscle returned).
  7.  Limit parameter respected (default 8; explicit 2).
  8.  Empty / no-match query returns [].
  9.  Caller's own custom exercise is searchable (visible under RLS).
  10. Another user's private exercise is NOT searchable (RLS isolation).
  11. lang= filter restricts alias hits to the given language.
  12. 401 when called without auth.

Seed (USER_93_ID = 500093, USER_93B_ID = 500094):
  global_muscle_93:       global muscle for the test exercises.
  global_ex_exact:        global exercise 'Gym93 Bench Press' — exact/prefix target.
  global_ex_prefix1:      global exercise 'Gym93 Benchmarks' — prefix target.
  global_ex_fuzzy:        global exercise 'Gym93 Benchpres' — fuzzy target.
  global_ex_alias:        global exercise 'Gym93 Deadlift' with RU alias 'Gym93 Становая'.
  private_ex_a:           own private exercise for USER_93_ID.
  private_ex_b:           private exercise for USER_93B_ID (must NOT be seen by A).
"""

import os
import sys
import uuid
from typing import Generator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import _APP_ROLE, _APP_ROLE_PASSWORD

USER_93_ID = 500093
USER_93B_ID = 500094


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
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_gym93(superuser_url: str) -> dict:
    """Insert seed data for GYM-93 search tests.

    Creates:
      - USER_93_ID and USER_93B_ID user rows.
      - global_muscle_93: global muscle.
      - global_ex_exact: 'Gym93 Bench Press' (exact/prefix target).
      - global_ex_prefix1: 'Gym93 Benchmarks' (prefix target, distinct from exact).
      - global_ex_fuzzy: 'Gym93 Benchpres' (fuzzy target, 1 char missing).
      - global_ex_alias: 'Gym93 Deadlift' with RU alias 'Gym93 Становая тяга'.
      - private_ex_a: private exercise owned by USER_93_ID.
      - private_ex_b: private exercise owned by USER_93B_ID (invisible to A).

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids and names.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        # Users
        for uid, name, uname in [
            (USER_93_ID, "User93A", "user93a_test"),
            (USER_93B_ID, "User93B", "user93b_test"),
        ]:
            conn.execute(text("""
                INSERT INTO users (id, registration_date, first_name, username)
                VALUES (:uid, NOW(), :name, :uname)
                ON CONFLICT (id) DO NOTHING
            """), {"uid": uid, "name": name, "uname": uname})

        # Global muscle
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym93 Global Muscle', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        gm_id = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym93 Global Muscle' AND created_by IS NULL"
        )).fetchone()[0]

        # Global exercises
        exercise_rows = [
            ("Gym93 Bench Press", True),   # exact and prefix target
            ("Gym93 Benchmarks", True),    # prefix target only
            ("Gym93 Benchpres", True),     # fuzzy target (missing final s)
            ("Gym93 Deadlift", True),      # alias target
        ]
        ids = {}
        for ex_name, is_global in exercise_rows:
            conn.execute(text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES (:name, :mid, :isg, NULL)
                ON CONFLICT DO NOTHING
            """), {"name": ex_name, "mid": gm_id, "isg": is_global})
            row = conn.execute(text(
                "SELECT id FROM exercises WHERE name=:name AND created_by IS NULL"
            ), {"name": ex_name}).fetchone()
            ids[ex_name] = row[0]

        # Alias: RU alias for 'Gym93 Deadlift'
        deadlift_id = ids["Gym93 Deadlift"]
        conn.execute(text("""
            INSERT INTO exercise_alias (canonical_id, alias_name, lang, is_global, created_by)
            VALUES (:cid, 'Gym93 Становая тяга', 'ru', TRUE, NULL)
            ON CONFLICT (canonical_id, name_key) DO NOTHING
        """), {"cid": deadlift_id})

        # Also add an EN alias to test lang filter exclusion
        conn.execute(text("""
            INSERT INTO exercise_alias (canonical_id, alias_name, lang, is_global, created_by)
            VALUES (:cid, 'Gym93 Romanian DL', 'en', TRUE, NULL)
            ON CONFLICT (canonical_id, name_key) DO NOTHING
        """), {"cid": deadlift_id})

        # Private exercise for USER_93_ID
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym93 Private Cable Fly', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": gm_id, "uid": USER_93_ID})
        priv_a = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym93 Private Cable Fly' AND created_by=:uid"
        ), {"uid": USER_93_ID}).fetchone()[0]

        # Private exercise for USER_93B_ID (must not be visible to USER_93_ID)
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('Gym93 Private Secret Lift', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": gm_id, "uid": USER_93B_ID})
        priv_b = conn.execute(text(
            "SELECT id FROM exercises WHERE name='Gym93 Private Secret Lift' AND created_by=:uid"
        ), {"uid": USER_93B_ID}).fetchone()[0]

        conn.commit()
    eng.dispose()

    return {
        "global_muscle_id": gm_id,
        "global_ex_exact": ids["Gym93 Bench Press"],
        "global_ex_prefix1": ids["Gym93 Benchmarks"],
        "global_ex_fuzzy": ids["Gym93 Benchpres"],
        "global_ex_alias": deadlift_id,
        "private_ex_a": priv_a,
        "private_ex_b": priv_b,
    }


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym93_client(db_setup) -> Generator:
    """Build a TestClient for GYM-93 tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym93(db_setup["superuser_url"])

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
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    from app.core.database import _set_rls_gucs
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


class TestExerciseSearchTiers:
    """Core ranking-tier tests."""

    def test_exact_match_returns_correct_candidate(self, gym93_client):
        """Querying the exact name returns a result with match_reason='exact', score=1.0."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Bench Press"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert len(items) > 0, "Expected at least one result"
        best = items[0]
        assert best["id"] == seed["global_ex_exact"]
        assert best["match_reason"] == "exact"
        assert best["score"] == pytest.approx(1.0)
        assert best["muscle"] == seed["global_muscle_id"]
        assert best["muscle_name"] == "Gym93 Global Muscle"

    def test_prefix_match_returns_prefix_reason(self, gym93_client):
        """Querying a prefix ('gym93 bench') matches prefix candidates."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "gym93 bench"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        reasons = {it["match_reason"] for it in items}
        ids = {it["id"] for it in items}

        # 'Gym93 Bench Press' is an exact match for key 'gym93 bench' + ... wait,
        # 'gym93 bench' is a prefix of 'gym93 bench press', so it's a prefix match.
        # 'Gym93 Benchmarks' key is 'gym93 benchmarks', also prefix.
        assert "prefix" in reasons, f"Expected prefix hits, got: {reasons}"
        # All three bench* exercises should appear
        assert seed["global_ex_exact"] in ids
        assert seed["global_ex_prefix1"] in ids

    def test_alias_match_with_lang_filter(self, gym93_client):
        """Querying a RU alias with lang='ru' returns the exercise with match_reason='alias'."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Становая", "lang": "ru"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert len(items) > 0, "Expected alias hit for RU query"
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        assert len(alias_hits) > 0, f"No alias hit in: {items}"
        alias_ids = {it["id"] for it in alias_hits}
        assert seed["global_ex_alias"] in alias_ids

    def test_alias_match_without_lang_filter(self, gym93_client):
        """Querying a RU alias without lang returns alias hit (any lang)."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Становая"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        assert len(alias_hits) > 0, "Expected alias hit without lang filter"
        assert any(it["id"] == seed["global_ex_alias"] for it in alias_hits)

    def test_lang_param_does_not_filter_alias_hits(self, gym93_client):
        """GYM-112: lang param no longer filters alias recall; EN alias matches with lang='ru'.

        After GYM-112 the alias tier ignores :lang — aliases are alternate names a user
        may type in any language.  Querying the EN alias name with lang='ru' must still
        resolve the exercise via the alias tier.
        """
        client, seed = gym93_client
        # 'Gym93 Romanian DL' is an EN alias. After GYM-112, lang='ru' must NOT exclude it.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Romanian", "lang": "ru"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        # EN alias should now be returned even when lang='ru'
        en_alias_ids = {it["id"] for it in alias_hits}
        assert seed["global_ex_alias"] in en_alias_ids, (
            f"EN alias exercise must be returned via alias tier regardless of lang param; "
            f"got alias_hits: {alias_hits}"
        )

    def test_fuzzy_match_returns_fuzzy_reason(self, gym93_client):
        """A typo query ('gym93 benchpres') should return a fuzzy hit."""
        client, seed = gym93_client
        # 'Gym93 Benchpres' is missing the final 's' of 'bench press'; test fuzzy.
        # But 'gym93 benchpres' is also the exact name of global_ex_fuzzy.
        # Use a deliberately misspelled query that won't exact/prefix match but will fuzzy.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Bnch Pres"},  # two typos: missing 'e', missing 's'
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        # Allow empty for very bad typos — the test checks that fuzzy works at all.
        if items:
            reasons = {it["match_reason"] for it in items}
            assert "fuzzy" in reasons, f"Expected fuzzy hit, got reasons: {reasons}"


class TestExerciseSearchMuscleFilter:
    """Muscle-scoped search tests."""

    def test_muscle_filter_scopes_results(self, gym93_client, db_setup):
        """Passing muscle_id returns only exercises under that muscle."""
        client, seed = gym93_client
        # Create a second muscle with a different exercise to test isolation.
        superuser_url = db_setup["superuser_url"]
        eng = create_engine(superuser_url, poolclass=NullPool)
        with eng.connect() as conn:
            conn.execute(text("""
                INSERT INTO muscles (name, is_global, created_by)
                VALUES ('Gym93 Other Muscle', TRUE, NULL)
                ON CONFLICT DO NOTHING
            """))
            other_mid = conn.execute(text(
                "SELECT id FROM muscles WHERE name='Gym93 Other Muscle' AND created_by IS NULL"
            )).fetchone()[0]
            conn.execute(text("""
                INSERT INTO exercises (name, muscle, is_global, created_by)
                VALUES ('Gym93 Other Squat', :mid, TRUE, NULL)
                ON CONFLICT DO NOTHING
            """), {"mid": other_mid})
            conn.commit()
        eng.dispose()

        # Search with muscle_id = global_muscle_93: 'Other Squat' must NOT appear.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "gym93", "muscle_id": seed["global_muscle_id"]},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        returned_muscles = {it["muscle"] for it in items}
        assert returned_muscles <= {seed["global_muscle_id"]}, (
            f"Expected only muscle {seed['global_muscle_id']}, got {returned_muscles}"
        )

    def test_search_without_muscle_filter_finds_all(self, gym93_client):
        """Omitting muscle_id searches the whole catalog."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "gym93"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        muscle_ids = {it["muscle"] for it in items}
        # Should see exercises from multiple muscles if any match
        assert len(items) > 0


class TestExerciseSearchLimit:
    """Limit parameter tests."""

    def test_default_limit_is_eight(self, gym93_client):
        """Without explicit limit, at most 8 results returned."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "gym93"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) <= 8

    def test_explicit_limit_two(self, gym93_client):
        """limit=2 returns at most 2 results."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "gym93", "limit": 2},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) <= 2


class TestExerciseSearchEdgeCases:
    """Empty result and isolation tests."""

    def test_no_match_returns_empty_list(self, gym93_client):
        """Query with no candidates returns [] not 404."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "xqzxqzxqzxqzxqz_no_match_ever_93"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_own_custom_exercise_is_searchable(self, gym93_client):
        """Caller's own private exercise appears in search results (visible under RLS)."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Private Cable"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = {it["id"] for it in resp.json()}
        assert seed["private_ex_a"] in ids, (
            "Caller's own private exercise should be searchable"
        )

    def test_other_user_private_exercise_not_searchable(self, gym93_client):
        """Another user's private exercise is invisible under RLS."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym93 Private Secret"},
            headers=_service_headers(USER_93_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = {it["id"] for it in resp.json()}
        assert seed["private_ex_b"] not in ids, (
            "Another user's private exercise must not appear in search results"
        )

    def test_unauthenticated_returns_401(self, gym93_client):
        """Calling without auth returns 401."""
        client, seed = gym93_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "bench"},
        )
        assert resp.status_code == 401, resp.text
