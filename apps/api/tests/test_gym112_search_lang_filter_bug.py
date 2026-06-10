"""GYM-112 regression test: exercise-search alias tier must match regardless of UI lang.

Root cause: the alias tier previously had ``AND a.lang = :lang``, so Russian aliases
(``lang='ru'``) were excluded when the caller passed ``lang='en'`` — a Cyrillic query
returned nothing even though the alias existed.

This file covers the exact live failure plus the surrounding cases:
  1. RU query + lang='en' (the broken case) → alias hit (regression guard).
  2. RU query + lang='ru' (was working) → alias hit still works after fix.
  3. RU query + no lang → alias hit.
  4. Muscle scoping is preserved: alias hit respects muscle_id filter.
  5. English query unaffected (exact/prefix tiers, no lang involved).

Seed: one canonical exercise (Gym112 Barbell Bench Press) + one RU alias
(Gym112 Жим штанги лёжа) under a global muscle.  Uses the shared db_setup /
conftest DB fixture (postgres:16, full schema + Alembic migrations).
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

USER_112_ID = 500112

_CANONICAL_NAME = "Gym112 Barbell Bench Press"
_RU_ALIAS = "Gym112 Жим штанги лёжа"
_RU_QUERY_PREFIX = "Gym112 Жим"   # prefix to exercise the prefix-match arm of alias tier

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


def _seed_gym112(superuser_url: str) -> dict:
    """Insert seed data for GYM-112 regression tests.

    Creates:
      - USER_112_ID user row.
      - Gym112 Global Muscle: global muscle.
      - Gym112 Barbell Bench Press: global canonical exercise.
      - Gym112 Жим штанги лёжа: RU alias for the canonical exercise.

    Args:
        superuser_url: Superuser connection URL.

    Returns:
        Dict with keys ``muscle_id``, ``exercise_id``.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        # User
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User112', 'user112_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_112_ID})

        # Global muscle
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym112 Global Muscle', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        muscle_id = conn.execute(text(
            "SELECT id FROM muscles "
            "WHERE name = 'Gym112 Global Muscle' AND created_by IS NULL"
        )).scalar_one()

        # Canonical exercise
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES (:name, :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"name": _CANONICAL_NAME, "mid": muscle_id})
        exercise_id = conn.execute(text(
            "SELECT id FROM exercises WHERE name = :name AND created_by IS NULL"
        ), {"name": _CANONICAL_NAME}).scalar_one()

        # RU alias
        conn.execute(text("""
            INSERT INTO exercise_alias
                (canonical_id, alias_name, lang, is_global, created_by)
            VALUES (:cid, :alias, 'ru', TRUE, NULL)
            ON CONFLICT (canonical_id, name_key) DO NOTHING
        """), {"cid": exercise_id, "alias": _RU_ALIAS})

        conn.commit()
    eng.dispose()

    return {"muscle_id": muscle_id, "exercise_id": exercise_id}


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient + seed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym112_client(db_setup) -> Generator:
    """Build a TestClient for GYM-112 regression tests with dedicated seed data.

    Args:
        db_setup: Session fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym112(db_setup["superuser_url"])

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


class TestGym112AliasLangRegressions:
    """GYM-112 regression: alias tier must not filter by UI locale."""

    def test_ru_alias_found_with_lang_en(self, gym112_client):
        """REGRESSION: RU alias must resolve when caller passes lang='en'.

        This was the live failure: the operator's Telegram UI locale is 'en',
        so lang='en' was sent, and the alias tier's ``a.lang = 'en'`` excluded
        all ``lang='ru'`` aliases — a Russian query returned nothing.
        """
        client, seed = gym112_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": _RU_QUERY_PREFIX, "lang": "en"},
            headers=_service_headers(USER_112_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        assert alias_hits, (
            f"Expected at least one alias hit for q={_RU_QUERY_PREFIX!r} lang='en'; "
            f"got empty result.  This is the GYM-112 regression."
        )
        hit_ids = {it["id"] for it in alias_hits}
        assert seed["exercise_id"] in hit_ids, (
            f"Exercise {seed['exercise_id']} ({_CANONICAL_NAME!r}) not resolved via alias "
            f"with q={_RU_QUERY_PREFIX!r} lang='en'; alias_hits: {alias_hits}"
        )

    def test_ru_alias_found_with_lang_ru(self, gym112_client):
        """RU alias still works when caller passes lang='ru' (was already working)."""
        client, seed = gym112_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": _RU_QUERY_PREFIX, "lang": "ru"},
            headers=_service_headers(USER_112_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        assert alias_hits, (
            f"Expected alias hit for q={_RU_QUERY_PREFIX!r} lang='ru'; got: {items}"
        )
        assert any(it["id"] == seed["exercise_id"] for it in alias_hits), (
            f"Exercise {seed['exercise_id']} not in alias hits: {alias_hits}"
        )

    def test_ru_alias_found_without_lang(self, gym112_client):
        """RU alias resolves when lang param is omitted entirely."""
        client, seed = gym112_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": _RU_QUERY_PREFIX},
            headers=_service_headers(USER_112_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        alias_hits = [it for it in items if it["match_reason"] == "alias"]
        assert alias_hits, (
            f"Expected alias hit for q={_RU_QUERY_PREFIX!r} (no lang); got: {items}"
        )
        assert any(it["id"] == seed["exercise_id"] for it in alias_hits)

    def test_muscle_scope_respected_with_ru_alias(self, gym112_client):
        """Muscle scoping is unaffected: alias hit respects muscle_id filter."""
        client, seed = gym112_client

        # Scoped to the correct muscle: should find the exercise.
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": _RU_QUERY_PREFIX, "lang": "en",
                    "muscle_id": seed["muscle_id"]},
            headers=_service_headers(USER_112_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        hit_ids = {it["id"] for it in items if it["match_reason"] == "alias"}
        assert seed["exercise_id"] in hit_ids, (
            f"Alias hit expected under correct muscle_id={seed['muscle_id']}; got: {items}"
        )

        # Scoped to a non-existent muscle id: should return empty.
        resp2 = client.get(
            "/api/v1/exercises/search",
            params={"q": _RU_QUERY_PREFIX, "lang": "en", "muscle_id": 999999},
            headers=_service_headers(USER_112_ID),
        )
        assert resp2.status_code == 200, resp2.text
        assert resp2.json() == [], (
            "Search scoped to a non-existent muscle must return []"
        )

    def test_english_search_unaffected(self, gym112_client):
        """English canonical name still resolves via exact/prefix tiers."""
        client, seed = gym112_client
        resp = client.get(
            "/api/v1/exercises/search",
            params={"q": "Gym112 Barbell", "lang": "en"},
            headers=_service_headers(USER_112_ID),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()
        assert items, f"Expected English prefix hit; got empty result"
        match_reasons = {it["match_reason"] for it in items}
        assert match_reasons <= {"exact", "prefix", "fuzzy"}, (
            f"English query should hit exact/prefix/fuzzy tiers; got: {match_reasons}"
        )
        hit_ids = {it["id"] for it in items}
        assert seed["exercise_id"] in hit_ids, (
            f"Canonical exercise {seed['exercise_id']} not found by English prefix query"
        )
