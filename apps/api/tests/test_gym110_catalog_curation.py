"""GYM-110 — integration test for the 0008 catalog-curation migration.

Spins up an ephemeral ``postgres:16`` (or reuses ``TEST_DATABASE_URL``),
loads ``init.sql``, stamps ``0001_baseline``, seeds a REPRESENTATIVE catalog
(the 5 merge sources + their targets, the junk id 337, two muscles, the operator
olykov 2107709598 AND another user, and training rows on merge sources + on a
demote target + on another user's row), then runs ``alembic upgrade head`` so the
0008 migration executes, and asserts the curation invariants:

- total ``training`` count unchanged; each merge source's sets now sit on its
  target (sum preserved); zero training rows with a non-existent exercise_id;
- merge sources (26, 347, 351, 338, 40) and junk 337 are GONE from ``exercises``;
- DEMOTE rows: is_global=false, created_by=operator, renamed;
- KEEP rows renamed; both name_key partial unique indexes still satisfied.

This test is self-contained (its own throwaway DB) so it controls the catalog
state the migration mutates, independent of conftest's shared seed.
"""

import os
import socket
import subprocess
import time
import uuid
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_INIT_SQL = os.path.join(_REPO_ROOT, "packages", "db", "init.sql")
_ALEMBIC_DIR = os.path.join(_REPO_ROOT, "packages", "db")

_SUPERUSER = "postgres"
_SUPERPASSWORD = "testpw"
_DBNAME = "gym110test"

OPERATOR_ID = 2107709598          # olykov — DEMOTE created_by target
OTHER_USER_ID = 343459661         # the user who owns the 367 sets (KEEP, do not move)

# Merge map under test: source -> target (from canonical_curation.tsv v3.1).
MERGE_MAP = {26: 127, 347: 54, 351: 362, 338: 30, 40: 373}
MERGE_SOURCES = tuple(MERGE_MAP.keys())
JUNK_ID = 337

# A couple of representative KEEP / DEMOTE rows to assert renames on.
KEEP_RENAMES = {30: "Dumbbell Bench Press", 373: "Bulgarian Split Squat",
                127: "Reverse Barbell Curl", 54: "Cable Chest Press (Machine)",
                367: "Cable Leg Press"}
DEMOTE_RENAMES = {362: "Side Pressure (Dumbbell)", 48: "Bulgarian Split Squat (Barbell)",
                  339: "Cable Rope Lateral Raise"}


# ---------------------------------------------------------------------------
# Docker helpers (mirrors conftest, kept local so the test is self-contained)
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


# ---------------------------------------------------------------------------
# Seed a representative pre-curation catalog (raw SQL, ids forced).
# ---------------------------------------------------------------------------

def _seed_catalog(url: str) -> None:
    """Insert the muscles/users/exercises/training the curation will touch.

    Exercise ids are forced to match the worksheet (the migration is keyed on
    id). After inserting, the SERIAL sequence is bumped past the max id.
    """
    eng = create_engine(url, poolclass=NullPool)
    with eng.connect() as conn:
        # Users: operator (DEMOTE target) + another user (owns 367's sets).
        conn.execute(text("""
            INSERT INTO users (id, registration_date, first_name, username)
            VALUES (:op, NOW(), 'Olykov', 'olykov'),
                   (:other, NOW(), 'Other', 'other_user')
            ON CONFLICT (id) DO NOTHING
        """), {"op": OPERATOR_ID, "other": OTHER_USER_ID})

        # Global muscles matching the worksheet groupings. Note 351 (Forearms)
        # and 362 (Biceps) share a name_key but live in DIFFERENT muscles, so the
        # global partial unique (name_key, muscle) is NOT violated — exactly the
        # prod reality the migration must preserve.
        muscle_names = ("Biceps", "Chest", "Forearms", "Legs", "Shoulders")
        for mname in muscle_names:
            conn.execute(text("""
                INSERT INTO muscles (name, is_global, created_by)
                VALUES (:n, TRUE, NULL) ON CONFLICT DO NOTHING
            """), {"n": mname})
        mid = {
            mname: conn.execute(text(
                "SELECT id FROM muscles WHERE name=:n AND created_by IS NULL"
            ), {"n": mname}).scalar_one()
            for mname in muscle_names
        }
        chest, legs, biceps, forearms = (
            mid["Chest"], mid["Legs"], mid["Biceps"], mid["Forearms"]
        )
        shoulders = mid["Shoulders"]

        # Exercises with FORCED ids = the worksheet ids the migration acts on.
        # (current_name pre-curation; the migration renames them.) Muscles match
        # the worksheet groupings above.
        rows = [
            # merge sources (global, operator's single-user data)
            (26,  "Barbell brachialis curls", biceps, True,  None),
            (347, "Chest press machine (2)",  chest, True,  None),
            (351, "Side pressure - dumbbell", forearms, True, None),  # Forearms
            (338, "Bench press dumbbell",     chest, True,  None),
            (40,  "Smith Bulgarian split squats", legs, True, None),
            # merge targets
            (127, "Reverse curl barbell",     biceps, True,  None),
            (54,  "Chest press machine",      chest, True,  None),
            (362, "Side pressure dumbbell",   biceps, True,  None),  # Biceps; becomes DEMOTE
            (30,  "Dumbbell press flat bench", chest, True, None),
            (373, "Bulgarian split squats dumbbell", legs, True, None),
            # a KEEP row owned/used by another user (must NOT be demoted/moved)
            (367, "Leg press cable",          legs,  True,  None),
            # representative DEMOTE rows
            (48,  "Bulgarian split squats",   legs,  True,  None),
            (339, "Cable rope lateral delt rows", shoulders, True, None),
            # junk row (0 sets, not in worksheet)
            (337, "Bench press incline-delete1", chest, True, None),
        ]
        for ex_id, name, muscle, is_global, created_by in rows:
            conn.execute(text("""
                INSERT INTO exercises (id, name, muscle, is_global, created_by)
                VALUES (:id, :name, :muscle, :is_global, :created_by)
                ON CONFLICT (id) DO NOTHING
            """), {"id": ex_id, "name": name, "muscle": muscle,
                   "is_global": is_global, "created_by": created_by})

        # Bump the SERIAL past the forced ids so future inserts don't collide.
        conn.execute(text(
            "SELECT setval(pg_get_serial_sequence('exercises','id'), "
            "(SELECT MAX(id) FROM exercises))"
        ))

        # Per-exercise muscle for training rows (matches the catalog rows above).
        ex_muscle = {26: biceps, 347: chest, 351: forearms, 338: chest, 40: legs,
                     30: chest, 373: legs, 127: biceps, 54: chest, 362: biceps}

        # Training rows. Per the worksheet set-counts; operator owns all merge-source
        # sets; 367 holds 2 sets from OTHER_USER_ID. Use small counts that preserve
        # the worksheet's relative sums (exact counts below).
        # source -> number of sets to seed on that source (pre-merge)
        source_sets = {26: 3, 347: 3, 351: 0, 338: 2, 40: 2}
        for src, n in source_sets.items():
            for _ in range(n):
                conn.execute(text("""
                    INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                    VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 100.0, 10.0)
                """), {"tid": uuid.uuid4().hex[:32], "uid": OPERATOR_ID,
                       "mid": ex_muscle[src], "eid": src})

        # Pre-existing sets already on some merge TARGETS (must be preserved + summed).
        for tgt, n in {30: 4, 373: 4, 127: 2}.items():
            for _ in range(n):
                conn.execute(text("""
                    INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                    VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 80.0, 8.0)
                """), {"tid": uuid.uuid4().hex[:32], "uid": OPERATOR_ID,
                       "mid": ex_muscle[tgt], "eid": tgt})

        # A demote target (362) with a couple of operator sets (history must stay on it).
        for _ in range(2):
            conn.execute(text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 50.0, 12.0)
            """), {"tid": uuid.uuid4().hex[:32], "uid": OPERATOR_ID,
                   "mid": ex_muscle[362], "eid": 362})

        # 367 — 2 sets from ANOTHER user (KEEP; cannot move someone else's data).
        for _ in range(2):
            conn.execute(text("""
                INSERT INTO training (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                VALUES (:tid, NOW(), :uid, :mid, :eid, 1, 200.0, 5.0)
            """), {"tid": uuid.uuid4().hex[:32], "uid": OTHER_USER_ID,
                   "mid": legs, "eid": 367})

        conn.commit()
    eng.dispose()


def _alembic_upgrade(url: str) -> None:
    env = {**os.environ, "DATABASE_URL": url}
    for cmd in (["alembic", "stamp", "0001_baseline"],
                ["alembic", "upgrade", "head"]):
        subprocess.run(cmd, cwd=_ALEMBIC_DIR, env=env, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# ---------------------------------------------------------------------------
# Module-scoped fixture: own throwaway DB, seeded BEFORE upgrade.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def curated_db() -> Generator[str, None, None]:
    """Yield a superuser URL for a DB where 0008 has been applied to seed data."""
    test_url = os.getenv("TEST_DATABASE_URL")
    container_id = None

    if test_url:
        url = test_url
    else:
        if not _docker_available():
            pytest.skip("Docker unavailable and TEST_DATABASE_URL unset; "
                        "cannot run the GYM-110 migration integration test.")
        port = _free_port()
        name = f"gym110_{uuid.uuid4().hex[:8]}"
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
        url = f"postgresql://{_SUPERUSER}:{_SUPERPASSWORD}@127.0.0.1:{port}/{_DBNAME}"

    try:
        # init.sql (schema) -> stamp baseline -> seed pre-curation catalog -> upgrade.
        with open(_INIT_SQL, encoding="utf-8") as f:
            _run_sql(url, f.read())
        # Stamp baseline first so seed happens on the bootstrapped schema, then
        # upgrade runs 0008 against the seeded catalog. We seed BEFORE upgrade.
        env = {**os.environ, "DATABASE_URL": url}
        subprocess.run(["alembic", "stamp", "0001_baseline"], cwd=_ALEMBIC_DIR,
                       env=env, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        _seed_catalog(url)
        subprocess.run(["alembic", "upgrade", "head"], cwd=_ALEMBIC_DIR,
                       env=env, check=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    except Exception as exc:
        if container_id:
            subprocess.run(["docker", "stop", container_id],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out = getattr(exc, "stderr", b"")
        pytest.fail(f"GYM-110 DB setup failed: {exc} :: {out!r}")

    yield url

    if container_id:
        subprocess.run(["docker", "stop", container_id],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture(scope="module")
def conn(curated_db: str):
    eng = create_engine(curated_db, poolclass=NullPool)
    with eng.connect() as c:
        yield c
    eng.dispose()


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

def test_merge_sources_and_junk_deleted(conn) -> None:
    """All 5 merge sources and junk id 337 are removed from exercises."""
    gone = list(MERGE_SOURCES) + [JUNK_ID]
    rows = conn.execute(
        text("SELECT id FROM exercises WHERE id = ANY(:ids)"), {"ids": gone}
    ).fetchall()
    assert rows == [], f"expected these ids gone, still present: {[r[0] for r in rows]}"


def test_total_training_count_unchanged(conn) -> None:
    """The migration repoints sets; it never adds or drops training rows.

    Seeded sets: sources 3+3+0+2+2=10, target pre-existing 4+4+2=10,
    362 demote-target 2, 367 other-user 2  => 24 total.
    """
    total = conn.execute(text("SELECT COUNT(*) FROM training")).scalar_one()
    assert total == 24, f"training count changed: {total} != 24"


def test_no_orphan_training_rows(conn) -> None:
    """No training row references a non-existent exercise_id."""
    orphans = conn.execute(text("""
        SELECT COUNT(*) FROM training t
        WHERE t.exercise_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM exercises e WHERE e.id = t.exercise_id)
    """)).scalar_one()
    assert orphans == 0, f"{orphans} orphaned training rows"


def test_merge_sets_summed_onto_targets(conn) -> None:
    """Each merge source's sets now sit on its target; sums are preserved.

    target 30  = own 4 + 338's 2  = 6
    target 373 = own 4 + 40's  2  = 6
    target 127 = own 2 + 26's  3  = 5
    target 54  = own 0 + 347's 3  = 3
    target 362 = own 2 + 351's 0  = 2  (351 had 0 sets)
    """
    expected = {30: 6, 373: 6, 127: 5, 54: 3, 362: 2}
    for tgt, exp in expected.items():
        n = conn.execute(
            text("SELECT COUNT(*) FROM training WHERE exercise_id = :id"),
            {"id": tgt},
        ).scalar_one()
        assert n == exp, f"target {tgt}: {n} sets != expected {exp}"
    # And no training references any deleted source.
    leftover = conn.execute(
        text("SELECT COUNT(*) FROM training WHERE exercise_id = ANY(:ids)"),
        {"ids": list(MERGE_SOURCES)},
    ).scalar_one()
    assert leftover == 0, f"{leftover} training rows still point at a merge source"


def test_demote_rows_personal_and_renamed(conn) -> None:
    """DEMOTE rows: is_global=false, created_by=operator, renamed."""
    for ex_id, name in DEMOTE_RENAMES.items():
        row = conn.execute(text(
            "SELECT name, is_global, created_by FROM exercises WHERE id = :id"
        ), {"id": ex_id}).fetchone()
        assert row is not None, f"demote row {ex_id} missing"
        assert row[0] == name, f"id {ex_id} name {row[0]!r} != {name!r}"
        assert row[1] is False, f"id {ex_id} still is_global"
        assert row[2] == OPERATOR_ID, f"id {ex_id} created_by {row[2]} != operator"


def test_keep_rows_renamed_and_global(conn) -> None:
    """KEEP rows renamed; still public; 367 stays untouched-ownership."""
    for ex_id, name in KEEP_RENAMES.items():
        row = conn.execute(text(
            "SELECT name, is_global, created_by FROM exercises WHERE id = :id"
        ), {"id": ex_id}).fetchone()
        assert row is not None, f"keep row {ex_id} missing"
        assert row[0] == name, f"id {ex_id} name {row[0]!r} != {name!r}"
        assert row[1] is True, f"id {ex_id} should remain global"
        assert row[2] is None, f"id {ex_id} should remain created_by NULL"


def test_name_key_unique_indexes_satisfied(conn) -> None:
    """Both partial unique indexes on name_key hold after curation.

    A violation would have failed the migration, but assert explicitly: no
    duplicate (name_key, muscle) among globals, none in (name_key, muscle,
    created_by) among personals.
    """
    dup_global = conn.execute(text("""
        SELECT name_key, muscle, COUNT(*) c FROM exercises
        WHERE created_by IS NULL
        GROUP BY name_key, muscle HAVING COUNT(*) > 1
    """)).fetchall()
    assert dup_global == [], f"global name_key collisions: {dup_global}"

    dup_user = conn.execute(text("""
        SELECT name_key, muscle, created_by, COUNT(*) c FROM exercises
        WHERE created_by IS NOT NULL
        GROUP BY name_key, muscle, created_by HAVING COUNT(*) > 1
    """)).fetchall()
    assert dup_user == [], f"user name_key collisions: {dup_user}"


def test_migration_is_rerunnable(conn) -> None:
    """Re-running upgrade head is a no-op (sources already gone, ids stable)."""
    # The fixture already upgraded once; running head again must not error and
    # must leave the catalog identical.
    before = conn.execute(text("SELECT COUNT(*) FROM exercises")).scalar_one()
    before_tr = conn.execute(text("SELECT COUNT(*) FROM training")).scalar_one()
    url = conn.engine.url.render_as_string(hide_password=False)
    env = {**os.environ, "DATABASE_URL": url}
    conn.rollback()  # drop our snapshot so the re-run's committed state is visible
    subprocess.run(["alembic", "upgrade", "head"], cwd=_ALEMBIC_DIR, env=env,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    conn.rollback()
    after = conn.execute(text("SELECT COUNT(*) FROM exercises")).scalar_one()
    after_tr = conn.execute(text("SELECT COUNT(*) FROM training")).scalar_one()
    assert (before, before_tr) == (after, after_tr)
