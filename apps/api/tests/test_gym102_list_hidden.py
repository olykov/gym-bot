"""GYM-102: Integration tests for list-hidden muscles/exercises endpoints.

Covers:
  1. GET /muscles/hidden — returns exactly the muscles the caller has hidden.
     - hiding a global muscle + an own muscle → both returned with correct is_mine.
     - none hidden → empty array (200, not 404).
  2. GET /exercises/hidden?muscle=<name> — returns exactly the exercises the
     caller has hidden within the resolved muscle.
     - hide a couple of exercises → list returns exactly those two.
     - variant-case muscle name resolves via name_key (e.g. "gym102 chest" →
       same row as "GYM102 Chest").
     - none hidden → empty array.
  3. hide-own-muscle end-to-end:
     - after hiding an own muscle it is gone from GET /muscles (visible list).
     - it IS present in GET /muscles/hidden with is_mine=True.
     - unhide via DELETE /muscles/{id}/hidden restores it to the visible list.
     - unhide removes it from the hidden list.

Seed (USER_102_ID = 500102):
  - global_muscle: "GYM102 Chest" (is_global=True, created_by=NULL).
  - own_muscle: "GYM102 Own Muscle" (is_global=False, created_by=USER_102_ID).
  - own_muscle_hide_target: "GYM102 Hide Target Muscle" (own, used for end-to-end hide test).
  - global_ex_1: "GYM102 Bench Press" under global_muscle.
  - global_ex_2: "GYM102 Cable Fly" under global_muscle.
  - own_ex: "GYM102 Own Exercise" under own_muscle.

Relies on the session-scoped ``db_setup`` fixture from ``conftest.py``.
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

USER_102_ID = 500102


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
    # Non-reachable Redis — cache calls degrade gracefully.
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_gym102(superuser_url: str) -> dict:
    """Insert seed data for GYM-102 tests.

    Creates:
    - USER_102_ID user row.
    - global_muscle: "GYM102 Chest" (global).
    - own_muscle: "GYM102 Own Muscle" (private, owned by USER_102_ID).
    - hide_target_muscle: "GYM102 Hide Target Muscle" (private, owned).
    - global_ex_1: "GYM102 Bench Press" under global_muscle.
    - global_ex_2: "GYM102 Cable Fly" under global_muscle.
    - own_ex: "GYM102 Own Exercise" under own_muscle.

    Does NOT pre-hide anything — each test hides/unhides via the API so they
    can assert clean before/after state.

    Args:
        superuser_url: Superuser URL for the target database.

    Returns:
        Dict of seed ids.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:uid, NOW(), 'User102', 'user102_test')
            ON CONFLICT (id) DO NOTHING
        """), {"uid": USER_102_ID})

        # Global muscle.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM102 Chest', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        global_muscle = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM102 Chest' AND created_by IS NULL"
        )).fetchone()[0]

        # Own muscle.
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM102 Own Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_102_ID})
        own_muscle = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM102 Own Muscle' AND created_by=:uid"
        ), {"uid": USER_102_ID}).fetchone()[0]

        # Own hide-target muscle (used in the end-to-end hide-own-muscle test).
        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('GYM102 Hide Target Muscle', FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"uid": USER_102_ID})
        hide_target_muscle = conn.execute(text(
            "SELECT id FROM muscles WHERE name='GYM102 Hide Target Muscle' AND created_by=:uid"
        ), {"uid": USER_102_ID}).fetchone()[0]

        # Global exercises under global_muscle.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM102 Bench Press', :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"mid": global_muscle})
        global_ex_1 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM102 Bench Press' AND muscle=:mid"
        ), {"mid": global_muscle}).fetchone()[0]

        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM102 Cable Fly', :mid, TRUE, NULL)
            ON CONFLICT DO NOTHING
        """), {"mid": global_muscle})
        global_ex_2 = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM102 Cable Fly' AND muscle=:mid"
        ), {"mid": global_muscle}).fetchone()[0]

        # Own exercise under own_muscle.
        conn.execute(text("""
            INSERT INTO exercises (name, muscle, is_global, created_by)
            VALUES ('GYM102 Own Exercise', :mid, FALSE, :uid)
            ON CONFLICT DO NOTHING
        """), {"mid": own_muscle, "uid": USER_102_ID})
        own_ex = conn.execute(text(
            "SELECT id FROM exercises WHERE name='GYM102 Own Exercise' AND created_by=:uid"
        ), {"uid": USER_102_ID}).fetchone()[0]

        # Ensure no pre-existing hidden rows for this user (idempotent test setup).
        conn.execute(text(
            "DELETE FROM user_hidden_muscles WHERE user_id=:uid"
        ), {"uid": USER_102_ID})
        conn.execute(text(
            "DELETE FROM user_hidden_exercises WHERE user_id=:uid"
        ), {"uid": USER_102_ID})

        conn.commit()
    eng.dispose()

    return {
        "global_muscle": global_muscle,
        "own_muscle": own_muscle,
        "hide_target_muscle": hide_target_muscle,
        "global_ex_1": global_ex_1,
        "global_ex_2": global_ex_2,
        "own_ex": own_ex,
    }


def _clean_hidden(superuser_url: str) -> None:
    """Remove all hidden rows for USER_102_ID to reset state between tests.

    Args:
        superuser_url: Superuser URL.
    """
    eng = create_engine(superuser_url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text(
            "DELETE FROM user_hidden_muscles WHERE user_id=:uid"
        ), {"uid": USER_102_ID})
        conn.execute(text(
            "DELETE FROM user_hidden_exercises WHERE user_id=:uid"
        ), {"uid": USER_102_ID})
        conn.commit()
    eng.dispose()


# ---------------------------------------------------------------------------
# Module-scoped fixture: TestClient wired to the test DB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gym102_client(db_setup) -> Generator:
    """Build a TestClient for GYM-102 tests with dedicated seed data.

    Args:
        db_setup: Session-scoped fixture providing the ephemeral postgres:16 setup.

    Yields:
        Tuple of (TestClient, seed_dict, db_setup_dict).
    """
    from urllib.parse import urlparse
    from fastapi.testclient import TestClient

    app_rw_url = db_setup["app_rw_url"]
    seed = _seed_gym102(db_setup["superuser_url"])

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
    from sqlalchemy.pool import NullPool

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
    yield client, seed, db_setup

    db_module.SessionLocal = original_session_local
    test_engine.dispose()


# ---------------------------------------------------------------------------
# 1. GET /muscles/hidden
# ---------------------------------------------------------------------------


class TestListHiddenMuscles:
    """GET /muscles/hidden returns exactly the caller's hidden muscles."""

    def test_no_hidden_muscles_returns_empty(self, gym102_client, db_setup):
        """Empty array when the user has no hidden muscles."""
        client, seed, _ = gym102_client
        _clean_hidden(db_setup["superuser_url"])

        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"

    def test_hide_global_and_own_muscle_both_returned(self, gym102_client, db_setup):
        """Hiding a global and an own muscle returns exactly those two."""
        client, seed, _ = gym102_client
        _clean_hidden(db_setup["superuser_url"])

        global_mid = seed["global_muscle"]
        own_mid = seed["own_muscle"]

        # Hide the global muscle.
        r1 = client.put(
            f"/api/v1/muscles/{global_mid}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert r1.status_code == 204, f"Expected 204, got {r1.status_code}: {r1.text}"

        # Hide the own muscle.
        r2 = client.put(
            f"/api/v1/muscles/{own_mid}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert r2.status_code == 204, f"Expected 204, got {r2.status_code}: {r2.text}"

        # List hidden — must return exactly the two hidden muscles.
        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        hidden_ids = {m["id"] for m in data}
        assert hidden_ids == {global_mid, own_mid}, (
            f"Expected exactly {{global_mid={global_mid}, own_mid={own_mid}}}, "
            f"got {hidden_ids}"
        )

    def test_is_mine_correct_for_global_and_own(self, gym102_client, db_setup):
        """is_mine is False for the global muscle and True for the own muscle."""
        client, seed, _ = gym102_client
        # State carries forward from the previous test (both still hidden).
        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        by_id = {m["id"]: m for m in data}

        global_mid = seed["global_muscle"]
        own_mid = seed["own_muscle"]

        assert global_mid in by_id, f"Global muscle {global_mid} missing from hidden list"
        assert own_mid in by_id, f"Own muscle {own_mid} missing from hidden list"

        assert by_id[global_mid]["is_mine"] is False, (
            f"Global muscle must have is_mine=False, got {by_id[global_mid]['is_mine']}"
        )
        assert by_id[own_mid]["is_mine"] is True, (
            f"Own muscle must have is_mine=True, got {by_id[own_mid]['is_mine']}"
        )

    def test_resolution_is_null_in_hidden_list(self, gym102_client, db_setup):
        """resolution field is null for all muscles in the hidden list."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        for m in resp.json():
            assert m.get("resolution") is None, (
                f"Expected resolution=null, got {m.get('resolution')} for muscle {m['id']}"
            )


# ---------------------------------------------------------------------------
# 2. GET /exercises/hidden?muscle=<name>
# ---------------------------------------------------------------------------


class TestListHiddenExercises:
    """GET /exercises/hidden?muscle=<name> returns exactly the caller's hidden exercises."""

    def test_no_hidden_exercises_returns_empty(self, gym102_client, db_setup):
        """Empty array when the user has no hidden exercises in this muscle."""
        client, seed, _ = gym102_client
        _clean_hidden(db_setup["superuser_url"])

        resp = client.get(
            "/api/v1/exercises/hidden",
            params={"muscle": "GYM102 Chest"},
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json() == [], f"Expected empty list, got {resp.json()}"

    def test_hide_two_exercises_both_returned(self, gym102_client, db_setup):
        """Hiding two exercises under a muscle returns exactly those two."""
        client, seed, _ = gym102_client
        _clean_hidden(db_setup["superuser_url"])

        ex1 = seed["global_ex_1"]
        ex2 = seed["global_ex_2"]

        r1 = client.put(
            f"/api/v1/exercises/{ex1}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert r1.status_code == 204, f"Expected 204, got {r1.status_code}: {r1.text}"

        r2 = client.put(
            f"/api/v1/exercises/{ex2}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert r2.status_code == 204, f"Expected 204, got {r2.status_code}: {r2.text}"

        resp = client.get(
            "/api/v1/exercises/hidden",
            params={"muscle": "GYM102 Chest"},
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        hidden_ids = {e["id"] for e in data}
        assert hidden_ids == {ex1, ex2}, (
            f"Expected exactly {{ex1={ex1}, ex2={ex2}}}, got {hidden_ids}"
        )

    def test_variant_case_muscle_name_resolves(self, gym102_client, db_setup):
        """Variant-case muscle name resolves the same muscle via name_key."""
        client, seed, _ = gym102_client
        # Both exercises still hidden from the previous test.
        ex1 = seed["global_ex_1"]
        ex2 = seed["global_ex_2"]

        for variant in ("gym102 chest", "GYM102-CHEST", "gym102  chest"):
            resp = client.get(
                "/api/v1/exercises/hidden",
                params={"muscle": variant},
                headers=_service_headers(USER_102_ID),
            )
            assert resp.status_code == 200, (
                f"Variant '{variant}' returned {resp.status_code}: {resp.text}"
            )
            hidden_ids = {e["id"] for e in resp.json()}
            assert hidden_ids == {ex1, ex2}, (
                f"Variant '{variant}' → expected {{ex1, ex2}}, got {hidden_ids}"
            )

    def test_is_mine_correct_for_global_exercises(self, gym102_client, db_setup):
        """is_mine is False for global exercises in the hidden list."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/exercises/hidden",
            params={"muscle": "GYM102 Chest"},
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        for ex in resp.json():
            assert ex["is_mine"] is False, (
                f"Global exercise {ex['id']} must have is_mine=False, got {ex['is_mine']}"
            )

    def test_unknown_muscle_returns_404(self, gym102_client, db_setup):
        """Unknown muscle name returns 404."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/exercises/hidden",
            params={"muscle": "No Such Muscle XYZ"},
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown muscle, got {resp.status_code}: {resp.text}"
        )

    def test_resolution_is_null_in_hidden_exercise_list(self, gym102_client, db_setup):
        """resolution field is null for all exercises in the hidden list."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/exercises/hidden",
            params={"muscle": "GYM102 Chest"},
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        for ex in resp.json():
            assert ex.get("resolution") is None, (
                f"Expected resolution=null, got {ex.get('resolution')} for exercise {ex['id']}"
            )


# ---------------------------------------------------------------------------
# 3. Hide-own-muscle end-to-end
# ---------------------------------------------------------------------------


class TestHideOwnMuscleEndToEnd:
    """Hide-own muscle: gone from visible list, present in hidden list, unhide restores."""

    def test_own_muscle_visible_before_hide(self, gym102_client, db_setup):
        """Own muscle appears in GET /muscles (visible list) before hiding."""
        client, seed, _ = gym102_client
        _clean_hidden(db_setup["superuser_url"])

        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["hide_target_muscle"] in ids, (
            f"Expected hide_target_muscle={seed['hide_target_muscle']} in visible list: {ids}"
        )

    def test_hide_own_muscle_returns_204(self, gym102_client, db_setup):
        """PUT /muscles/{id}/hidden for an own muscle returns 204."""
        client, seed, _ = gym102_client
        mid = seed["hide_target_muscle"]
        resp = client.put(
            f"/api/v1/muscles/{mid}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when hiding own muscle, got {resp.status_code}: {resp.text}"
        )

    def test_own_muscle_absent_from_visible_list_after_hide(self, gym102_client, db_setup):
        """After hiding, the own muscle is gone from GET /muscles."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["hide_target_muscle"] not in ids, (
            f"Expected hide_target_muscle absent from visible list after hide: {ids}"
        )

    def test_own_muscle_present_in_hidden_list_after_hide(self, gym102_client, db_setup):
        """After hiding, the own muscle appears in GET /muscles/hidden with is_mine=True."""
        client, seed, _ = gym102_client
        mid = seed["hide_target_muscle"]
        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        by_id = {m["id"]: m for m in data}
        assert mid in by_id, (
            f"Expected hide_target_muscle={mid} in hidden list: {[m['id'] for m in data]}"
        )
        assert by_id[mid]["is_mine"] is True, (
            f"Expected is_mine=True for own hidden muscle, got {by_id[mid]['is_mine']}"
        )

    def test_unhide_own_muscle_returns_204(self, gym102_client, db_setup):
        """DELETE /muscles/{id}/hidden (unhide) returns 204."""
        client, seed, _ = gym102_client
        mid = seed["hide_target_muscle"]
        resp = client.delete(
            f"/api/v1/muscles/{mid}/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 204, (
            f"Expected 204 when unhiding own muscle, got {resp.status_code}: {resp.text}"
        )

    def test_own_muscle_restored_to_visible_list_after_unhide(self, gym102_client, db_setup):
        """After unhiding, the own muscle reappears in GET /muscles."""
        client, seed, _ = gym102_client
        resp = client.get(
            "/api/v1/muscles",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert seed["hide_target_muscle"] in ids, (
            f"Expected hide_target_muscle restored in visible list after unhide: {ids}"
        )

    def test_own_muscle_absent_from_hidden_list_after_unhide(self, gym102_client, db_setup):
        """After unhiding, the own muscle is gone from GET /muscles/hidden."""
        client, seed, _ = gym102_client
        mid = seed["hide_target_muscle"]
        resp = client.get(
            "/api/v1/muscles/hidden",
            headers=_service_headers(USER_102_ID),
        )
        assert resp.status_code == 200, resp.text
        ids = [m["id"] for m in resp.json()]
        assert mid not in ids, (
            f"Expected hide_target_muscle absent from hidden list after unhide: {ids}"
        )
