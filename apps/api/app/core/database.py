"""SQLAlchemy engine, session factory, and RLS GUC wiring.

The runtime engine connects as ``app_rw`` (NOSUPERUSER NOBYPASSRLS) so that
Postgres RLS policies take effect.  The superuser ``DATABASE_URL`` (myuser) is
kept in config for Alembic and ops tooling only — never used here.

RLS GUC injection:
    A ``Session after_begin`` event listener runs at the start of every
    transaction (including read-only ones) and emits:

        SELECT set_config('app.user_id', :uid, true),
               set_config('app.role', :role, true)

    with ``is_local=true`` so the values reset automatically at transaction end,
    preventing any leakage across pooled connections.

    The event reads from the ``contextvars`` in ``app.core.db_context``, which
    are populated by the ``get_principal`` dependency (and its admin variants)
    and reset when the dependency tears down.  An unset contextvar defaults to
    ``''`` (empty string), which the policy reads as NULL → 0 visible rows
    (fail-closed guarantee).

Event choice — ``Session.after_begin``:
    ``after_begin`` fires after SQLAlchemy begins a new DBAPI transaction.  It
    receives the live DBAPI connection so we can execute raw SQL without going
    through the ORM.  Crucially it fires for both read and write transactions,
    and it re-fires after each commit+new-begin within the same session, so the
    GUCs are always fresh for the current transaction.
"""
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.db_context import current_role, current_user_id

logger = logging.getLogger(__name__)

settings = get_settings()

# Runtime engine — connects as app_rw; RLS policies apply.
engine = create_engine(settings.APP_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(SessionLocal, "after_begin")
def _set_rls_gucs(session: Session, transaction: object, connection: object) -> None:
    """Inject per-request RLS GUCs at the start of every transaction.

    Reads the current ``contextvars`` values and emits a ``set_config`` call
    with ``is_local=true`` so the GUC resets automatically at transaction end.

    Empty string (the contextvar default) is passed as-is; the RLS policy's
    ``nullif(..., '')::bigint`` then evaluates to NULL, matching no row
    (fail-closed).

    Args:
        session: The SQLAlchemy session that just began a transaction.
        transaction: SQLAlchemy ``SessionTransaction`` object (unused).
        connection: The DBAPI-level connection for this transaction.
    """
    uid = current_user_id.get()
    role = current_role.get()
    logger.debug("after_begin: set_config user_id=%r role=%r", uid, role)
    # Use connection.execute(text(...)) — works with SQLAlchemy 2.x Connection.
    connection.execute(
        text(
            "SELECT set_config('app.user_id', :uid, true),"
            " set_config('app.role', :role, true)"
        ),
        {"uid": uid, "role": role},
    )


def get_db():
    """Yield a SQLAlchemy session and close it when the request is done.

    The session is bound to the ``app_rw`` engine, so all queries execute
    under the RLS policies installed by the 0002_rls migration.

    Yields:
        An active ``Session`` instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
