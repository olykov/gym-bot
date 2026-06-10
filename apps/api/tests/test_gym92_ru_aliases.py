"""GYM-92 — integration test for the 0009 Russian-alias seed migration.

Self-contained (its own throwaway ``postgres:16``, like the GYM-110 test) so it
controls the catalog state the migration seeds, independent of conftest's shared
seed. The flow:

1. Load ``init.sql`` (schema), create the ``app_rw`` low-privilege role, stamp
   ``0001_baseline``.
2. Seed the catalog the 0009 INSERTs depend on: the 98 KEEP exercise ids (forced
   to the worksheet ids, the FK targets) under a few global muscles, plus the
   operator user. Seeding happens BEFORE the upgrade so the FK
   ``exercise_alias.canonical_id REFERENCES exercises(id)`` resolves.
3. ``alembic upgrade head`` — runs 0009, seeding the 98 ``lang='ru'`` aliases.

Then it asserts, against the real DB:
- all 98 ru aliases exist (``count(*) WHERE lang='ru'`` == 98);
- ``name_key`` is the GENERATED ``app_name_key(alias_name)`` for a sample;
- ON CONFLICT idempotency: re-running ``upgrade head`` inserts nothing;
- every alias FK resolves (no dangling ``canonical_id``);

and — END-TO-END through the real ``GET /exercises/search`` endpoint under
``app_rw`` (RLS active, GUC-wired exactly like prod) — that a Russian query
``Жим штанги лёжа`` with ``lang='ru'`` resolves to exercise id 7
('Barbell Bench Press') via the alias tier (``match_reason == 'alias'``).
"""

import os
import socket
import subprocess
import sys
import time
import uuid
from typing import Generator
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_INIT_SQL = os.path.join(_REPO_ROOT, "packages", "db", "init.sql")
_ALEMBIC_DIR = os.path.join(_REPO_ROOT, "packages", "db")
_RU_TSV = os.path.join(_REPO_ROOT, "packages", "db", "seeds", "exercise_aliases_ru.tsv")

_SUPERUSER = "postgres"
_SUPERPASSWORD = "testpw"
_DBNAME = "gym92test"
_APP_ROLE = "app_rw"
_APP_ROLE_PASSWORD = "app_rw_test_pw"

OPERATOR_ID = 2107709598  # olykov — the seeded user the endpoint acts as.

# Service token shared across the whole suite (conftest / GYM-93 use the same
# value). Settings is cached process-wide, so all endpoint tests MUST agree on
# the token, otherwise whichever module clears the cache last wins.
_SERVICE_TOKEN = "test_bot_service_token_rls"

# Spot-check ids the e2e/name_key assertions key on (must be 0009 KEEP rows).
BENCH_ID = 7              # 'Barbell Bench Press' — RU 'Жим штанги лёжа'.
BENCH_NAME = "Barbell Bench Press"
BENCH_RU = "Жим штанги лёжа"


# ---------------------------------------------------------------------------
# Load the 98 (canonical_id, ru_alias) pairs straight from the migration so the
# test asserts against exactly what the migration embeds (one source of truth).
# ---------------------------------------------------------------------------

def _load_migration_aliases() -> tuple[tuple[int, str], ...]:
    import importlib.util

    path = os.path.join(_ALEMBIC_DIR, "alembic", "versions", "0009_seed_ru_aliases.py")
    spec = importlib.util.spec_from_file_location("m0009", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.RU_ALIASES


RU_ALIASES = _load_migration_aliases()
EXPECTED_RU_COUNT = len(RU_ALIASES)  # 98


# ---------------------------------------------------------------------------
# Docker helpers (mirror conftest/GYM-110, kept local so the test is self-contained)
# ---------------------------------------------------------------------------

def _docker_available() -> bool:
    try:
        return subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=5,
        ).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_pg(host: str, port: int, dbname: str, timeout: int = 60) -> None:
    import psycopg2
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            psycopg2.connect(host=host, port=port, dbname=dbname,
                             user=_SUPERUSER, password=_SUPERPASSWORD,
                             connect_timeout=2).close()
            return
        except psycopg2.OperationalError:
            time.sleep(1)
    raise TimeoutError(f"Postgres not up on {host}:{port} in {timeout}s")


def _run_sql(url: str, sql: str) -> None:
    eng = create_engine(url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    eng.dispose()


def _create_app_role(url: str) -> None:
    """Create the low-privilege ``app_rw`` role the API connects as under RLS."""
    sql = f"""
        DO $bootstrap$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN
                EXECUTE format(
                    'CREATE ROLE {_APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS '
                    'NOCREATEDB NOCREATEROLE PASSWORD %L',
                    '{_APP_ROLE_PASSWORD}'
                );
            END IF;
        END
        $bootstrap$;
        GRANT USAGE ON SCHEMA public TO {_APP_ROLE};
        GRANT CONNECT ON DATABASE {_DBNAME} TO {_APP_ROLE};
    """
    _run_sql(url, sql)


# ---------------------------------------------------------------------------
# Seed the 98 KEEP canonical exercises (the FK targets) + the operator.
# ---------------------------------------------------------------------------

def _seed_keep_catalog(url: str) -> None:
    """Insert the 98 KEEP exercises (forced ids) the 0009 aliases reference.

    Each alias's ``canonical_id`` must exist in ``exercises`` for the FK to hold,
    so we seed exactly the 98 ids the migration embeds. Names/muscles are
    representative (the migration keys only on id and only seeds aliases).
    """
    eng = create_engine(url, poolclass=NullPool)
    with eng.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:op, NOW(), 'Olykov', 'olykov')
            ON CONFLICT (id) DO NOTHING
        """), {"op": OPERATOR_ID})

        conn.execute(text("""
            INSERT INTO muscles (name, is_global, created_by)
            VALUES ('Gym92 Global Muscle', TRUE, NULL)
            ON CONFLICT DO NOTHING
        """))
        muscle_id = conn.execute(text(
            "SELECT id FROM muscles WHERE name='Gym92 Global Muscle' AND created_by IS NULL"
        )).scalar_one()

        # One global exercise per KEEP id, forced to the worksheet id. English
        # canonical name = the 0008 KEEP name; for id 7 we use the real name so
        # the e2e assertion can verify the resolved exercise by name too.
        for ex_id, _ru in RU_ALIASES:
            name = BENCH_NAME if ex_id == BENCH_ID else f"Gym92 Exercise {ex_id}"
            conn.execute(text("""
                INSERT INTO exercises (id, name, muscle, is_global, created_by)
                VALUES (:id, :name, :mid, TRUE, NULL)
                ON CONFLICT (id) DO NOTHING
            """), {"id": ex_id, "name": name, "mid": muscle_id})

        # Bump the SERIAL past the forced ids so later inserts don't collide.
        conn.execute(text(
            "SELECT setval(pg_get_serial_sequence('exercises','id'), "
            "(SELECT MAX(id) FROM exercises))"
        ))
        conn.commit()
    eng.dispose()


def _alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(["alembic", *args], cwd=_ALEMBIC_DIR, env=env, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# ---------------------------------------------------------------------------
# Module fixture: throwaway DB seeded BEFORE 0009 runs.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded_db() -> Generator[dict, None, None]:
    """Yield {superuser_url, app_rw_url} for a DB with 0009 applied."""
    test_url = os.getenv("TEST_DATABASE_URL")
    container_id = None

    if test_url:
        superuser_url = test_url
        parsed = urlparse(test_url)
        host, port, dbname = parsed.hostname, parsed.port or 5432, parsed.path.lstrip("/")
    else:
        if not _docker_available():
            pytest.skip("Docker unavailable and TEST_DATABASE_URL unset; "
                        "cannot run the GYM-92 migration integration test.")
        port = _free_port()
        host, dbname = "127.0.0.1", _DBNAME
        name = f"gym92_{uuid.uuid4().hex[:8]}"
        run = subprocess.run(
            ["docker", "run", "--rm", "-d", "--name", name,
             "-e", f"POSTGRES_PASSWORD={_SUPERPASSWORD}",
             "-e", f"POSTGRES_DB={_DBNAME}",
             "-p", f"{port}:5432", "postgres:16"],
            capture_output=True, text=True)
        if run.returncode != 0:
            pytest.fail(f"Failed to start postgres:16: {run.stderr}")
        container_id = run.stdout.strip()
        try:
            _wait_for_pg("127.0.0.1", port, _DBNAME, timeout=60)
        except TimeoutError as exc:
            subprocess.run(["docker", "stop", container_id],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pytest.fail(str(exc))
        superuser_url = f"postgresql://{_SUPERUSER}:{_SUPERPASSWORD}@127.0.0.1:{port}/{_DBNAME}"

    app_rw_url = f"postgresql://{_APP_ROLE}:{_APP_ROLE_PASSWORD}@{host}:{port}/{dbname}"

    try:
        with open(_INIT_SQL, encoding="utf-8") as f:
            _run_sql(superuser_url, f.read())
        _create_app_role(superuser_url)
        _alembic(superuser_url, "stamp", "0001_baseline")
        _seed_keep_catalog(superuser_url)          # seed FK targets BEFORE upgrade
        _alembic(superuser_url, "upgrade", "head")  # runs 0009
    except Exception as exc:
        if container_id:
            subprocess.run(["docker", "stop", container_id],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out = getattr(exc, "stderr", b"")
        pytest.fail(f"GYM-92 DB setup failed: {exc} :: {out!r}")

    yield {"superuser_url": superuser_url, "app_rw_url": app_rw_url}

    if container_id:
        subprocess.run(["docker", "stop", container_id],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture(scope="module")
def conn(seeded_db: dict):
    eng = create_engine(seeded_db["superuser_url"], poolclass=NullPool)
    with eng.connect() as c:
        yield c
    eng.dispose()


# ---------------------------------------------------------------------------
# DB-level assertions
# ---------------------------------------------------------------------------

def test_all_98_ru_aliases_seeded(conn) -> None:
    """Exactly the 98 ru-tagged aliases exist after upgrade."""
    n = conn.execute(
        text("SELECT count(*) FROM exercise_alias WHERE lang = 'ru'")
    ).scalar_one()
    assert n == EXPECTED_RU_COUNT, f"{n} ru aliases != {EXPECTED_RU_COUNT}"
    assert EXPECTED_RU_COUNT == 98, "expected 98 KEEP aliases in the migration"


def test_aliases_are_global_catalog_rows(conn) -> None:
    """Seeded aliases use the catalog defaults: is_global=TRUE, created_by NULL."""
    bad = conn.execute(text(
        "SELECT count(*) FROM exercise_alias "
        "WHERE lang = 'ru' AND (is_global IS NOT TRUE OR created_by IS NOT NULL)"
    )).scalar_one()
    assert bad == 0, f"{bad} ru aliases are not global/admin-owned"


def test_no_dangling_canonical_fk(conn) -> None:
    """Every ru alias's canonical_id resolves to an existing exercise (KEEP)."""
    orphans = conn.execute(text("""
        SELECT count(*) FROM exercise_alias a
        WHERE a.lang = 'ru'
          AND NOT EXISTS (SELECT 1 FROM exercises e WHERE e.id = a.canonical_id)
    """)).scalar_one()
    assert orphans == 0, f"{orphans} ru aliases point at a missing exercise"


def test_name_key_generated_correctly(conn) -> None:
    """name_key is the GENERATED app_name_key(alias_name) for the bench alias."""
    row = conn.execute(text("""
        SELECT a.name_key, public.app_name_key(:ru) AS expected
        FROM exercise_alias a
        WHERE a.canonical_id = :cid AND a.lang = 'ru' AND a.alias_name = :ru
    """), {"cid": BENCH_ID, "ru": BENCH_RU}).fetchone()
    assert row is not None, "bench RU alias missing"
    assert row[0] == row[1], f"name_key {row[0]!r} != app_name_key {row[1]!r}"


def test_every_alias_text_matches_migration(conn) -> None:
    """Each (canonical_id, ru) embedded in the migration is present verbatim."""
    rows = conn.execute(text(
        "SELECT canonical_id, alias_name FROM exercise_alias WHERE lang = 'ru'"
    )).fetchall()
    seeded = {(r[0], r[1]) for r in rows}
    expected = set(RU_ALIASES)
    assert seeded == expected, (
        f"missing: {expected - seeded}; unexpected: {seeded - expected}"
    )


def test_upgrade_is_idempotent(conn) -> None:
    """Re-running upgrade head inserts nothing (ON CONFLICT DO NOTHING)."""
    before = conn.execute(
        text("SELECT count(*) FROM exercise_alias WHERE lang = 'ru'")
    ).scalar_one()
    url = conn.engine.url.render_as_string(hide_password=False)
    conn.rollback()  # release snapshot so the re-run's committed state is visible
    _alembic(url, "upgrade", "head")
    conn.rollback()
    after = conn.execute(
        text("SELECT count(*) FROM exercise_alias WHERE lang = 'ru'")
    ).scalar_one()
    assert after == before == EXPECTED_RU_COUNT, (
        f"idempotency broken: before={before} after={after}"
    )


def test_downgrade_removes_ru_aliases(conn) -> None:
    """downgrade(0008) deletes exactly the ru aliases (reversible)."""
    url = conn.engine.url.render_as_string(hide_password=False)
    conn.rollback()
    _alembic(url, "downgrade", "0008_apply_catalog_curation")
    conn.rollback()
    n = conn.execute(
        text("SELECT count(*) FROM exercise_alias WHERE lang = 'ru'")
    ).scalar_one()
    assert n == 0, f"{n} ru aliases remain after downgrade"
    # Restore head so the e2e endpoint test (any order) still sees the aliases.
    _alembic(url, "upgrade", "head")
    conn.rollback()
    restored = conn.execute(
        text("SELECT count(*) FROM exercise_alias WHERE lang = 'ru'")
    ).scalar_one()
    assert restored == EXPECTED_RU_COUNT


# ---------------------------------------------------------------------------
# END-TO-END: real GET /exercises/search endpoint, app_rw + RLS, alias tier.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def search_client(seeded_db: dict):
    """Build a TestClient wired to the seeded DB as app_rw (RLS active)."""
    from fastapi.testclient import TestClient

    app_rw_url = seeded_db["app_rw_url"]
    parsed = urlparse(app_rw_url)

    # The actual DB binding is via the swapped db_module.SessionLocal below, not
    # via Settings — so we only need env vars Settings reads for AUTH. The service
    # token MUST match the rest of the suite (cached Settings is process-wide).
    os.environ["APP_DB_USER"] = _APP_ROLE
    os.environ["APP_DB_PASSWORD"] = _APP_ROLE_PASSWORD
    os.environ["DB_HOST"] = parsed.hostname or "127.0.0.1"
    os.environ["DB_PORT"] = str(parsed.port or 5432)
    os.environ["DB_NAME"] = parsed.path.lstrip("/")
    os.environ.setdefault("DB_USER", _SUPERUSER)
    os.environ.setdefault("DB_PASSWORD", _SUPERPASSWORD)
    os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_gym92_only")
    os.environ.setdefault("ADMIN_USER", "admin")
    os.environ.setdefault("ADMIN_PASSWORD", "adminpw")
    os.environ["BOT_SERVICE_TOKEN"] = _SERVICE_TOKEN
    os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost")
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/1")

    from app.core.config import get_settings
    get_settings.cache_clear()

    import app.core.database as db_module
    from app.core.database import _set_rls_gucs

    test_engine = create_engine(app_rw_url, poolclass=NullPool)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    event.listen(factory, "after_begin", _set_rls_gucs)

    original = db_module.SessionLocal
    db_module.SessionLocal = factory

    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    db_module.SessionLocal = original
    test_engine.dispose()


def _service_headers(user_id: int) -> dict:
    return {
        "X-Service-Token": _SERVICE_TOKEN,
        "X-Act-As-User": str(user_id),
    }


def test_e2e_ru_query_resolves_via_alias_tier(search_client) -> None:
    """RU query 'Жим штанги лёжа' (lang=ru) -> exercise 7 with match_reason 'alias'.

    Exercises the real search endpoint under app_rw + RLS: the only way id 7
    matches a Cyrillic query is through the seeded exercise_alias row (tier 3).
    """
    resp = search_client.get(
        "/api/v1/exercises/search",
        params={"q": BENCH_RU, "lang": "ru"},
        headers=_service_headers(OPERATOR_ID),
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    alias_hits = [it for it in items if it["match_reason"] == "alias"]
    assert alias_hits, f"no alias hit for RU query; got: {items}"
    hit = next((it for it in alias_hits if it["id"] == BENCH_ID), None)
    assert hit is not None, f"exercise {BENCH_ID} not resolved via alias; got: {items}"
    assert hit["name"] == BENCH_NAME, f"resolved name {hit['name']!r} != {BENCH_NAME!r}"
    assert hit["match_reason"] == "alias"


def test_e2e_ru_query_without_lang_still_resolves(search_client) -> None:
    """The same RU query without a lang filter still resolves via the alias."""
    resp = search_client.get(
        "/api/v1/exercises/search",
        params={"q": BENCH_RU},
        headers=_service_headers(OPERATOR_ID),
    )
    assert resp.status_code == 200, resp.text
    ids = {it["id"] for it in resp.json() if it["match_reason"] == "alias"}
    assert BENCH_ID in ids, f"exercise {BENCH_ID} not resolved without lang filter"
