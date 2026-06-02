"""Cross-tenant RLS isolation integration tests (GYM-36).

These tests prove — against a real Postgres 16 with the real 0002_rls
policies active — that the Row-Level Security layer is:

  * Correctly isolating per-user rows (user A cannot see/modify user B's data).
  * Fail-closed (no principal context → 0 visible rows).
  * Admin-bypassed (role='admin' sees everything).
  * Catalog-aware (global rows visible; only owner can modify private rows).

Every assertion goes through the app's Session + contextvar machinery
(``rls_session``) so the after_begin GUC wiring is exercised exactly as the
production API exercises it.

Seed layout (created in conftest._seed_data):
  - USER_A_ID (100001): private muscle A, private exercise A, 2 training rows,
    1 hidden-exercise row (hides B's private ex).
  - USER_B_ID (100002): private muscle B, private exercise B, 2 training rows,
    1 hidden-exercise row (hides A's private ex).
  - Global: 1 muscle (Global Chest), 1 exercise (Global Bench Press).
"""

import uuid
from typing import Optional

import pytest
from sqlalchemy.exc import IntegrityError

from tests.conftest import USER_A_ID, USER_B_ID, rls_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count(session, table: str, where: str = "", params: Optional[dict] = None) -> int:
    """Return COUNT(*) for a table, optionally with a WHERE clause.

    Args:
        session: Active SQLAlchemy session.
        table: Table name.
        where: Optional SQL WHERE clause (without the ``WHERE`` keyword).
        params: Bind parameters for the WHERE clause.

    Returns:
        Integer count of matching rows.
    """
    from sqlalchemy import text

    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = session.execute(text(sql), params or {}).fetchone()
    return row[0]


def _update_rows(session, table: str, where: str, params: dict) -> int:
    """Execute an UPDATE and return the number of rows affected.

    Args:
        session: Active SQLAlchemy session.
        table: Table name.
        where: SQL WHERE clause (without ``WHERE``).
        params: Bind parameters.

    Returns:
        Rowcount of the UPDATE statement.
    """
    from sqlalchemy import text

    result = session.execute(
        text(f"UPDATE {table} SET set=1 WHERE {where}"),
        params,
    )
    return result.rowcount


def _delete_rows(session, table: str, where: str, params: dict) -> int:
    """Execute a DELETE and return the number of rows affected.

    Args:
        session: Active SQLAlchemy session.
        table: Table name.
        where: SQL WHERE clause (without ``WHERE``).
        params: Bind parameters.

    Returns:
        Rowcount of the DELETE statement.
    """
    from sqlalchemy import text

    result = session.execute(
        text(f"DELETE FROM {table} WHERE {where}"),
        params,
    )
    return result.rowcount


# ---------------------------------------------------------------------------
# 1. User A sees only A's own rows
# ---------------------------------------------------------------------------

class TestUserAVisibility:
    """User A sees exactly the rows it owns — no more, no less."""

    def test_training_count(self, app_rw_session_factory, db_setup):
        """User A sees only A's 2 training rows."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "training")
        assert count == seed["training_a"]

    def test_private_muscle_visible(self, app_rw_session_factory, db_setup):
        """User A's private muscle is visible to A."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "muscles",
                           "id = :mid", {"mid": seed["priv_muscle_a"]})
        assert count == 1

    def test_private_exercise_visible(self, app_rw_session_factory, db_setup):
        """User A's private exercise is visible to A."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "exercises",
                           "id = :eid", {"eid": seed["priv_ex_a"]})
        assert count == 1

    def test_hidden_exercise_row_visible(self, app_rw_session_factory, db_setup):
        """User A's hidden-exercise row is visible only to A."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "user_hidden_exercises",
                           "user_id = :uid", {"uid": USER_A_ID})
        assert count == 1

    def test_users_row_visible(self, app_rw_session_factory):
        """User A can see its own users row."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "users", "id = :uid", {"uid": USER_A_ID})
        assert count == 1

    def test_global_muscle_visible(self, app_rw_session_factory, db_setup):
        """User A sees the global muscle (is_global=TRUE)."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "muscles",
                           "id = :mid", {"mid": seed["global_muscle_id"]})
        assert count == 1

    def test_global_exercise_visible(self, app_rw_session_factory, db_setup):
        """User A sees the global exercise."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "exercises",
                           "id = :eid", {"eid": seed["global_ex_id"]})
        assert count == 1


# ---------------------------------------------------------------------------
# 2. User A cannot access User B's rows
# ---------------------------------------------------------------------------

class TestCrossTenantIsolation:
    """User A gets 0 rows / 0 rowcount when targeting B's data."""

    def test_cannot_select_b_training(self, app_rw_session_factory):
        """User A sees 0 training rows belonging to user B."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "training",
                           "user_id = :uid", {"uid": USER_B_ID})
        assert count == 0

    def test_cannot_select_b_private_muscle(self, app_rw_session_factory, db_setup):
        """User A sees 0 results for B's private muscle."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "muscles",
                           "id = :mid", {"mid": seed["priv_muscle_b"]})
        assert count == 0

    def test_cannot_select_b_private_exercise(self, app_rw_session_factory, db_setup):
        """User A sees 0 results for B's private exercise."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "exercises",
                           "id = :eid", {"eid": seed["priv_ex_b"]})
        assert count == 0

    def test_cannot_select_b_users_row(self, app_rw_session_factory):
        """User A gets 0 rows when querying user B's users record."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "users", "id = :uid", {"uid": USER_B_ID})
        assert count == 0

    def test_cannot_select_b_hidden_exercise(self, app_rw_session_factory):
        """User A cannot see B's hidden-exercise entries."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            count = _count(s, "user_hidden_exercises",
                           "user_id = :uid", {"uid": USER_B_ID})
        assert count == 0

    def test_update_b_training_affects_zero_rows(self, app_rw_session_factory):
        """UPDATE targeting B's training from A's session touches 0 rows."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            rowcount = _update_rows(s, "training",
                                    "user_id = :uid", {"uid": USER_B_ID})
            s.rollback()
        assert rowcount == 0

    def test_delete_b_training_affects_zero_rows(self, app_rw_session_factory):
        """DELETE targeting B's training from A's session touches 0 rows."""
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            rowcount = _delete_rows(s, "training",
                                    "user_id = :uid", {"uid": USER_B_ID})
            s.rollback()
        assert rowcount == 0

    def test_insert_training_as_b_is_rejected(self, app_rw_session_factory, db_setup):
        """Inserting a training row with user_id=B while session is A raises."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            with pytest.raises(Exception):
                s.execute(
                    text("""
                        INSERT INTO training
                            (id, date, user_id, muscle_id, exercise_id, set, weight, reps)
                        VALUES
                            (:tid, NOW(), :uid, :mid, :eid, 1, 50.0, 5.0)
                    """),
                    {
                        "tid": uuid.uuid4().hex[:32],
                        "uid": USER_B_ID,
                        "mid": seed["priv_muscle_b"],
                        "eid": seed["priv_ex_b"],
                    },
                )
                s.flush()
            s.rollback()


# ---------------------------------------------------------------------------
# 3. No principal context → fail-closed (every table returns 0 rows)
# ---------------------------------------------------------------------------

class TestFailClosed:
    """Without a principal, user-owned tables return 0 rows (fail-closed).

    Catalog tables (muscles, exercises) expose global rows even without a
    principal because the SELECT policy is ``is_global OR created_by = me``.
    Global rows (created_by IS NULL, is_global=TRUE) are intentionally
    world-readable — they are catalog data.  Private rows (created_by IS NOT
    NULL) are still fail-closed.
    """

    @pytest.mark.parametrize("table", [
        "users",
        "training",
        "user_hidden_exercises",
        "user_hidden_muscles",
    ])
    def test_no_principal_zero_rows_user_tables(self, app_rw_session_factory, table):
        """With no GUC context, user-owned tables return 0 rows (fail-closed)."""
        with rls_session(app_rw_session_factory, user_id=None, role=None) as s:
            count = _count(s, table)
        assert count == 0, (
            f"Expected 0 rows in {table!r} with no principal, got {count}"
        )

    def test_no_principal_catalog_private_rows_hidden(
        self, app_rw_session_factory, db_setup
    ):
        """With no principal, private catalog rows (created_by IS NOT NULL) are hidden."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role=None) as s:
            count_a = _count(s, "muscles",
                             "id = :mid", {"mid": seed["priv_muscle_a"]})
            count_b = _count(s, "muscles",
                             "id = :mid", {"mid": seed["priv_muscle_b"]})
        assert count_a == 0, "Private muscle A should not be visible with no principal"
        assert count_b == 0, "Private muscle B should not be visible with no principal"

    def test_no_principal_catalog_global_rows_visible(
        self, app_rw_session_factory, db_setup
    ):
        """With no principal, global catalog rows (is_global=TRUE) remain visible.

        This is the intentional policy: public catalog data is world-readable.
        """
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role=None) as s:
            count = _count(s, "muscles",
                           "id = :mid", {"mid": seed["global_muscle_id"]})
        assert count == 1, "Global muscle should be visible even with no principal"

    def test_no_principal_private_exercises_hidden(
        self, app_rw_session_factory, db_setup
    ):
        """With no principal, private exercises (created_by IS NOT NULL) are hidden."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role=None) as s:
            count_a = _count(s, "exercises",
                             "id = :eid", {"eid": seed["priv_ex_a"]})
            count_b = _count(s, "exercises",
                             "id = :eid", {"eid": seed["priv_ex_b"]})
        assert count_a == 0
        assert count_b == 0


# ---------------------------------------------------------------------------
# 4. Admin role sees all rows
# ---------------------------------------------------------------------------

class TestAdminVisibility:
    """role='admin' bypasses per-user filters and sees every row."""

    def test_admin_sees_all_users(self, app_rw_session_factory):
        """Admin session: at least 2 users visible."""
        with rls_session(app_rw_session_factory, user_id=None, role="admin") as s:
            count = _count(s, "users")
        assert count >= 2

    def test_admin_sees_all_training(self, app_rw_session_factory, db_setup):
        """Admin session: sum of A's and B's training rows visible."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role="admin") as s:
            count = _count(s, "training")
        assert count >= seed["training_a"] + seed["training_b"]

    def test_admin_sees_all_muscles(self, app_rw_session_factory, db_setup):
        """Admin session: global + A's private + B's private muscles visible."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role="admin") as s:
            count = _count(s, "muscles")
        # 1 global + 1 per user = 3 minimum
        assert count >= 3

    def test_admin_sees_all_exercises(self, app_rw_session_factory):
        """Admin session: at least 3 exercises visible (global + 2 private)."""
        with rls_session(app_rw_session_factory, user_id=None, role="admin") as s:
            count = _count(s, "exercises")
        assert count >= 3

    def test_admin_sees_all_hidden_exercises(self, app_rw_session_factory, db_setup):
        """Admin session: sees hidden-exercise rows for all users."""
        seed = db_setup["seed"]
        with rls_session(app_rw_session_factory, user_id=None, role="admin") as s:
            count = _count(s, "user_hidden_exercises")
        assert count >= seed["hidden_ex_a"] + seed["hidden_ex_b"]


# ---------------------------------------------------------------------------
# 5. Catalog table (muscles / exercises) — ownership rules
# ---------------------------------------------------------------------------

class TestCatalogOwnership:
    """Catalog RLS: global visible; only owner can modify private; A cannot
    write global rows."""

    def test_user_can_create_own_private_exercise(
        self, app_rw_session_factory, db_setup
    ):
        """User A can INSERT a new private exercise owned by A."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        new_name = f"Test Private Ex {uuid.uuid4().hex[:6]}"
        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            s.execute(
                text("""
                    INSERT INTO exercises (name, muscle, is_global, created_by)
                    VALUES (:name, :mid, FALSE, :uid)
                """),
                {"name": new_name, "mid": seed["priv_muscle_a"], "uid": USER_A_ID},
            )
            s.commit()
            count = _count(s, "exercises",
                           "name = :n AND created_by = :uid",
                           {"n": new_name, "uid": USER_A_ID})
        assert count == 1

    def test_cannot_update_global_muscle(self, app_rw_session_factory, db_setup):
        """User A updating a global muscle (created_by NULL) touches 0 rows."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            result = s.execute(
                text("UPDATE muscles SET name=name WHERE id = :mid"),
                {"mid": seed["global_muscle_id"]},
            )
            rowcount = result.rowcount
            s.rollback()
        assert rowcount == 0

    def test_cannot_delete_global_muscle(self, app_rw_session_factory, db_setup):
        """User A deleting a global muscle touches 0 rows."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            result = s.execute(
                text("DELETE FROM muscles WHERE id = :mid"),
                {"mid": seed["global_muscle_id"]},
            )
            rowcount = result.rowcount
            s.rollback()
        assert rowcount == 0

    def test_can_update_own_private_muscle(self, app_rw_session_factory, db_setup):
        """User A can UPDATE its own private muscle (created_by = A)."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            result = s.execute(
                text("UPDATE muscles SET name=name WHERE id = :mid"),
                {"mid": seed["priv_muscle_a"]},
            )
            rowcount = result.rowcount
            s.rollback()
        assert rowcount == 1

    def test_cannot_update_b_private_muscle(self, app_rw_session_factory, db_setup):
        """User A cannot UPDATE B's private muscle."""
        seed = db_setup["seed"]
        from sqlalchemy import text

        with rls_session(app_rw_session_factory, user_id=USER_A_ID, role="user") as s:
            result = s.execute(
                text("UPDATE muscles SET name=name WHERE id = :mid"),
                {"mid": seed["priv_muscle_b"]},
            )
            rowcount = result.rowcount
            s.rollback()
        assert rowcount == 0
